import os
import sys
import time
import asyncio
import random
import certifi
import aiohttp
from threading import Thread
from typing import Literal, Optional
from flask import Flask

import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import motor.motor_asyncio

# ==========================================
# 0. FORCE UNBUFFERED STDOUT
# ==========================================
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

def log(msg: str):
    print(msg, flush=True)

# 1. Secret Files mount path (must run before importing core_data)
if os.path.exists('/etc/secrets'):
    sys.path.append('/etc/secrets')

try:
    import core_data as faction_data
except ModuleNotFoundError as e:
    log(f"⚠️ Warning: Failed to import core_data: {e}")
    class FactionDataFallback:
        SYSTEM_PROMPT = ""
        FACTION_PROMPT = ""
    faction_data = FactionDataFallback()

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024   # skip files bigger than 10 MB
MAX_TRACKED_USERS = 300                   # cap chat memory so RAM can't grow forever

# ==========================================
# 1. FLASK WEB SERVER FOR RENDER PORT BINDING
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Eternity status: Active", 200

@app.route('/health')
def health():
    return "OK", 200

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

server_thread = Thread(target=run_web_server, daemon=True)
server_thread.start()

# ==========================================
# 2. CONFIGURATION & ENV VARIABLES
# ==========================================
DISCORD_TOKEN = os.getenv('ETERNITY_TOKEN') or os.getenv('DISCORD_TOKEN')
PROXY_URL = os.getenv('DISCORD_PROXY_URL')
MONGO_URI = os.getenv('MONGO_URI')
OWNER_ID = int(os.getenv('OWNER_ID', 1477528681709830297))

API_KEYS = [
    os.getenv('GEMINI_API_KEY'),
    os.getenv('GEMINI_KEY_1'),
    os.getenv('GEMINI_KEY_2')
]
API_KEYS = [k for k in API_KEYS if k]

if not DISCORD_TOKEN:
    raise ValueError("ETERNITY_TOKEN or DISCORD_TOKEN must be set!")

if not API_KEYS:
    raise ValueError("At least one GEMINI API key must be set!")

# ==========================================
# 2b. WIRE UP THE PROXY
# ==========================================
if PROXY_URL:
    clean_proxy = PROXY_URL.rstrip('/')
    discord.http.Route.BASE = clean_proxy
    log(f"🌐 REST proxy active: routing API calls through {clean_proxy}")
else:
    log("⚠️ No DISCORD_PROXY_URL set — REST calls go directly to Discord.")

# ==========================================
# 3. DISCORD BOT CLASS DEFINITION
# ==========================================
class EternityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix='?',
            intents=intents,
            help_command=None,   # /help is the only help (no duplicate ?help)
        )

        self.SPECIAL_CHANNEL_ID = 1500095634588569600
        self.ADMIN_IDS = [1477528681709830297]
        self.MODERATOR_ROLE_ID = 1485660896746541259

        self.SYSTEM_PROMPT = getattr(faction_data, 'SYSTEM_PROMPT', '')
        self.session = None
        self.db_client = None
        self.db = None
        self.profiles = None

        self.conversation_history = {}
        self.chat_cooldowns = {}

    async def setup_hook(self):
        self.session = aiohttp.ClientSession(headers=DEFAULT_HEADERS)
        self.tree.on_error = self.on_app_command_error

        if MONGO_URI:
            try:
                self.db_client = motor.motor_asyncio.AsyncIOMotorClient(
                    MONGO_URI,
                    tlsCAFile=certifi.where()
                )
                self.db = self.db_client["eternal_faction_db"]
                self.profiles = self.db["user_profiles"]
                log("🛰️ MongoDB Atlas Pipeline: Connected to ClusterEternal successfully!")
            except Exception as e:
                log(f"MongoDB Async Error: {e}")
        else:
            log("⚠️ WARNING: MONGO_URI missing! Moderation logs will not be saved.")

        initial_extensions = ['cogs.moderation', 'cogs.reactions']
        if os.path.exists("cogs/utility.py"):
            initial_extensions.append('cogs.utility')
        elif os.path.exists("cogs/utilities.py"):
            initial_extensions.append('cogs.utilities')

        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
                log(f"⚡ Extension '{extension}' loaded successfully!")
            except Exception as e:
                log(f"❌ Failed to load extension '{extension}': {e}")

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        if self.db_client:
            self.db_client.close()
        await super().close()

    # ---------- Gemini ----------
    def _remember(self, user_id, role: str, text: str):
        """Append to a user's chat memory, capped per user and in total."""
        if user_id not in self.conversation_history:
            if len(self.conversation_history) >= MAX_TRACKED_USERS:
                oldest = next(iter(self.conversation_history))
                self.conversation_history.pop(oldest, None)
            self.conversation_history[user_id] = []
        hist = self.conversation_history[user_id]
        hist.append({"role": role, "parts": [text]})
        if len(hist) > 15:
            self.conversation_history[user_id] = hist[-15:]

    async def get_gemini_response(self, user_message: str, user_id, attachment_data=None) -> str:
        combined_instructions = (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"Core Faction Knowledge Base:\n{getattr(faction_data, 'FACTION_PROMPT', '')}"
        )

        track_history = attachment_data is None
        if track_history:
            self._remember(user_id, "user", user_message)
            contents_payload = self.conversation_history[user_id]
        else:
            contents_payload = [user_message, attachment_data]

        keys_to_try = API_KEYS.copy()
        random.shuffle(keys_to_try)

        models_to_attempt = [
            'gemini-3.6-flash',
            'gemini-3.5-flash-lite',
            'gemini-2.5-flash',
            'gemini-2.5-pro'
        ]

        for key in keys_to_try:
            genai.configure(api_key=key)
            for model_name in models_to_attempt:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=combined_instructions
                    )
                    response = await asyncio.to_thread(model.generate_content, contents_payload)
                    assistant_message = response.text

                    if track_history:
                        self._remember(user_id, "model", assistant_message)
                    return assistant_message

                except Exception as e:
                    error_str = str(e)
                    log(f"Error on current API key ({model_name}): {error_str}")

                    if "429" in error_str or "quota" in error_str.lower() or "resource_exhausted" in error_str.lower():
                        await asyncio.sleep(2)
                        continue
                    else:
                        break

        # Every attempt failed: remove the unanswered user turn so history stays valid
        if track_history and self.conversation_history.get(user_id):
            self.conversation_history[user_id].pop()

        return "💠 *The cosmic frequencies are currently overloaded, my friends! Let the stars align and try again in a brief moment!*"

    # ---------- Error handling ----------
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        name = interaction.command.name if interaction.command else "unknown"

        if isinstance(error, app_commands.CommandInvokeError) and \
           isinstance(error.original, discord.HTTPException) and error.original.status == 429:
            log(f"⚠️ 429 on /{name}: Discord API rate limit hit.")
            return

        if isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏰ *Cooling down. Try again in {error.retry_after:.0f}s.*"
        elif isinstance(error, app_commands.MissingPermissions):
            msg = "❌ You lack the permissions for that command."
        elif isinstance(error, app_commands.NoPrivateMessage):
            msg = "❌ This command only works inside a server."
        else:
            log(f"❌ Command Error in /{name}: {error!r}")
            msg = "💠 Something went wrong. Try again shortly."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

    async def on_ready(self):
        log(f'✨ {self.user.name} is fully online and active!')
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over ETERNAL"))

    # ---------- Message handling ----------
    async def on_message(self, message):
        if message.author.bot or message.mention_everyone:
            return

        if message.guild is None and message.author.id != OWNER_ID:
            try:
                await message.reply("🔒 Direct messages are disabled for AI processing. Please use the server channels!")
            except Exception:
                pass
            return

        if message.content.startswith(self.command_prefix):
            await self.process_commands(message)
            return

        # NOTE: the 💠 reaction and the cosmic GIF are handled by cogs/reactions.py only.
        content_lower = message.content.lower()
        if content_lower == "protect the faction":
            return

        is_gif = "tenor.com" in content_lower or "giphy.com" in content_lower
        if not is_gif and message.attachments:
            is_gif = any(att.filename.lower().endswith('.gif') for att in message.attachments)

        is_pinged_or_replied = self.user.mentioned_in(message)
        if not is_pinged_or_replied and message.reference:
            replied_to = message.reference.resolved or message.reference.cached_message
            if replied_to is None and message.reference.message_id:
                try:
                    replied_to = await message.channel.fetch_message(message.reference.message_id)
                except Exception:
                    replied_to = None
            if replied_to is not None and getattr(replied_to, "author", None) == self.user:
                is_pinged_or_replied = True

        name_called = "eternity" in content_lower
        should_reply = (message.channel.id == self.SPECIAL_CHANNEL_ID) or is_pinged_or_replied or name_called
        if not should_reply:
            return

        current_time = time.time()
        user_id = message.author.id
        last = self.chat_cooldowns.get(user_id)
        if last is not None and current_time - last < 5:
            remaining = int(5 - (current_time - last)) + 1
            try:
                await message.reply(
                    f"⏰ *Hold your energy, guardian! The cosmic core is cooling down. Wait {remaining}s.*",
                    delete_after=3, mention_author=False)
            except Exception:
                pass
            return
        self.chat_cooldowns[user_id] = current_time

        try:
            async with message.channel.typing():
                clean_message = message.content.replace(f'<@{self.user.id}>', '').replace(f'<@!{self.user.id}>', '').strip()

                if not clean_message and is_gif:
                    clean_message = "Scan this GIF asset I sent you!"
                elif not clean_message and message.attachments:
                    clean_message = "Scan this asset!"

                if not clean_message:
                    await message.reply("✨ The incoming frequency appears empty!", mention_author=False)
                    return

                attachment_data = None
                if message.attachments and self.session:
                    try:
                        att = message.attachments[0]
                        if att.content_type and att.size <= MAX_ATTACHMENT_BYTES:
                            async with self.session.get(att.url) as resp:
                                if resp.status == 200:
                                    attachment_data = {
                                        'mime_type': att.content_type.split(';')[0],
                                        'data': await resp.read(),
                                    }
                        elif att.size > MAX_ATTACHMENT_BYTES:
                            await message.reply("📦 That file is too large for me to scan (max 10 MB).",
                                                mention_author=False)
                            return
                    except Exception as err:
                        log(f"Vision direct parse warning: {err}")

                response = await self.get_gemini_response(clean_message, message.author.id, attachment_data)

                for i in range(0, len(response), 1900):
                    await message.reply(response[i:i + 1900], mention_author=False)

        except discord.errors.HTTPException as http_err:
            if http_err.status == 429:
                log("⚠️ Rate limited by Discord (429) while replying.")
            else:
                log(f"⚠️ HTTP error while replying: {http_err}")
        except Exception as err:
            log(f"❌ on_message error: {err!r}")

# ==========================================
# 4. GATEWAY EXECUTION
# ==========================================
async def start_gateway():
    retry_delay = 60
    attempt = 0

    while True:
        attempt += 1
        log(f"🚀 Initializing Gateway Attempt {attempt} (backoff cap 900s)...")
        bot = EternityBot()

        @bot.command(name='ping')
        async def ping(ctx):
            latency = round(bot.latency * 1000)
            await ctx.send(f"✨ Sparkling! Pong! My cosmic waves reached you in {latency}ms. Ready for action!")

        @bot.command(name='sync')
        async def sync(ctx, spec: Optional[Literal["clear", "global"]] = None):
            if ctx.author.id != OWNER_ID:
                return await ctx.send("❌ Security alert: You do not have permission to run this command.")

            if ctx.guild is None:
                return await ctx.send("❌ Please run this command inside a server channel, not in DMs!")

            if spec == "clear":
                await ctx.send("🧹 Clearing server-specific cached commands...")
                bot.tree.clear_commands(guild=ctx.guild)
                await bot.tree.sync(guild=ctx.guild)
                return await ctx.send("✨ Server cache cleared! Run `?sync` now to re-register.")

            if spec == "global":
                await ctx.send("🌐 Syncing commands globally...")
                try:
                    synced = await bot.tree.sync()
                    await ctx.send(f"✅ Synced **{len(synced)}** commands globally!")
                except Exception as e:
                    await ctx.send(f"❌ Global synchronization failed: {e}")
                return

            await ctx.send(f"🔄 Force-syncing slash commands directly to **{ctx.guild.name}**...")
            try:
                bot.tree.copy_global_to(guild=ctx.guild)
                synced = await bot.tree.sync(guild=ctx.guild)
                await ctx.send(f"✅ Successfully synced **{len(synced)}** slash commands INSTANTLY to this server!")
            except Exception as e:
                await ctx.send(f"❌ Guild synchronization failed: {e}")

        try:
            async with bot:
                await bot.start(DISCORD_TOKEN)
            log("✅ Bot shut down cleanly (logout requested). Exiting loop.")
            break
        except discord.LoginFailure:
            log("❌ Invalid Discord token. Fix ETERNITY_TOKEN / DISCORD_TOKEN and redeploy.")
            break
        except discord.errors.HTTPException as e:
            if e.status == 429:
                log(f"⚠️ DISCORD 429 RATE LIMIT (Attempt {attempt})! Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 900)
            else:
                log(f"❌ HTTP Error: {e}")
                await asyncio.sleep(15)
        except Exception as e:
            log(f"❌ Connection Error: {e}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(start_gateway())

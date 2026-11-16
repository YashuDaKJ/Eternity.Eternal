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

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

def log(msg: str):
    print(msg, flush=True)

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

DEFAULT_HEADERS = {"User-Agent": "Eternity Discord bot"}
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_TRACKED_USERS = 300

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

Thread(target=run_web_server, daemon=True).start()

DISCORD_TOKEN = os.getenv('ETERNITY_TOKEN') or os.getenv('DISCORD_TOKEN')
PROXY_URL = os.getenv('DISCORD_PROXY_URL')
MONGO_URI = os.getenv('MONGO_URI')
OWNER_ID = int(os.getenv('OWNER_ID', 1477528681709830297))
API_KEYS = [k for k in (os.getenv('GEMINI_API_KEY'), os.getenv('GEMINI_KEY_1'), os.getenv('GEMINI_KEY_2')) if k]
if not DISCORD_TOKEN:
    raise ValueError("ETERNITY_TOKEN or DISCORD_TOKEN must be set!")
if not API_KEYS:
    raise ValueError("At least one GEMINI API key must be set!")
if PROXY_URL:
    discord.http.Route.BASE = PROXY_URL.rstrip('/')

class EternityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='?', intents=intents, help_command=None)
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
                self.db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
                self.db = self.db_client["eternal_faction_db"]
                self.profiles = self.db["user_profiles"]
                log("🛰️ MongoDB Atlas connected.")
            except Exception as e:
                log(f"MongoDB Async Error: {e}")
        initial_extensions = ['cogs.moderation', 'cogs.reactions', 'cogs.community_admin']
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

    def _remember(self, user_id, role: str, text: str):
        if user_id not in self.conversation_history:
            if len(self.conversation_history) >= MAX_TRACKED_USERS:
                self.conversation_history.pop(next(iter(self.conversation_history)), None)
            self.conversation_history[user_id] = []
        history = self.conversation_history[user_id]
        history.append({"role": role, "parts": [text]})
        if len(history) > 15:
            self.conversation_history[user_id] = history[-15:]

    async def get_gemini_response(self, user_message: str, user_id, attachment_data=None) -> str:
        instructions = f"{self.SYSTEM_PROMPT}\n\nCore Faction Knowledge Base:\n{getattr(faction_data, 'FACTION_PROMPT', '')}"
        track = attachment_data is None
        if track:
            self._remember(user_id, "user", user_message)
            contents = self.conversation_history[user_id]
        else:
            contents = [user_message, attachment_data]
        for key in random.sample(API_KEYS, len(API_KEYS)):
            genai.configure(api_key=key)
            for model_name in ('gemini-2.5-flash', 'gemini-2.5-pro'):
                try:
                    model = genai.GenerativeModel(model_name=model_name, system_instruction=instructions)
                    response = await asyncio.to_thread(model.generate_content, contents)
                    answer = response.text
                    if track:
                        self._remember(user_id, "model", answer)
                    return answer
                except Exception as e:
                    log(f"Gemini error ({model_name}): {e}")
                    if "429" in str(e) or "quota" in str(e).lower():
                        await asyncio.sleep(2)
                    else:
                        break
        if track and self.conversation_history.get(user_id):
            self.conversation_history[user_id].pop()
        return "💠 The AI service is temporarily unavailable. Please try again shortly."

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        name = interaction.command.name if interaction.command else "unknown"
        log(f"❌ Command Error in /{name}: {error!r}")
        msg = "❌ You lack the required permission." if isinstance(error, app_commands.MissingPermissions) else "💠 Something went wrong. Try again shortly."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

    async def on_ready(self):
        log(f'✨ {self.user.name} is online!')
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over ETERNAL"))

    async def on_message(self, message):
        if message.author.bot or message.mention_everyone:
            return
        if message.guild is None and message.author.id != OWNER_ID:
            try:
                await message.reply("🔒 Direct messages are disabled for AI processing.")
            except discord.HTTPException:
                pass
            return
        if message.content.startswith(self.command_prefix):
            await self.process_commands(message)
            return
        if message.guild is None:
            return
        content_lower = message.content.lower()
        if content_lower == "protect the faction":
            return
        is_gif = "tenor.com" in content_lower or "giphy.com" in content_lower or any(a.filename.lower().endswith('.gif') for a in message.attachments)
        is_pinged = self.user.mentioned_in(message)
        name_called = "eternity" in content_lower
        if not (message.channel.id == self.SPECIAL_CHANNEL_ID or is_pinged or name_called):
            return
        now = time.time()
        last = self.chat_cooldowns.get(message.author.id)
        if last is not None and now - last < 5:
            return
        self.chat_cooldowns[message.author.id] = now
        try:
            clean = message.content.replace(f'<@{self.user.id}>', '').replace(f'<@!{self.user.id}>', '').strip()
            if not clean:
                clean = "Scan this GIF asset I sent you!" if is_gif else "Scan this asset!" if message.attachments else "Hello"
            attachment = None
            if message.attachments and self.session:
                att = message.attachments[0]
                if att.content_type and att.size <= MAX_ATTACHMENT_BYTES:
                    async with self.session.get(att.url) as resp:
                        if resp.status == 200:
                            attachment = {'mime_type': att.content_type.split(';')[0], 'data': await resp.read()}
            answer = await self.get_gemini_response(clean, message.author.id, attachment)
            for i in range(0, len(answer), 1900):
                await message.reply(answer[i:i + 1900], mention_author=False)
        except Exception as e:
            log(f"on_message error: {e!r}")

async def start_gateway():
    bot = EternityBot()
    @bot.command(name='ping')
    async def ping(ctx):
        await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")
    @bot.command(name='sync')
    async def sync(ctx, spec: Optional[Literal["clear", "global"]] = None):
        if ctx.author.id != OWNER_ID or ctx.guild is None:
            return await ctx.send("Owner-only; run this command in a server.")
        if spec == "global":
            synced = await bot.tree.sync()
        else:
            if spec == "clear":
                bot.tree.clear_commands(guild=ctx.guild)
            else:
                bot.tree.copy_global_to(guild=ctx.guild)
            synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"Synced {len(synced)} commands.")
    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(start_gateway())

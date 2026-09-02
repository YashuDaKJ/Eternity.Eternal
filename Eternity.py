import os
import sys
import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import core_data as faction_data
from flask import Flask
import time
import asyncio
import random
import certifi
import aiohttp
import motor.motor_asyncio
from threading import Thread
from typing import Literal, Optional

# --- ENVIRONMENT VARIABLE SE CLOUDFLARE WORKER PROXY URL FETCH KAREIN ---
WORKER_PROXY_URL = os.getenv('WORKER_PROXY_URL', 'https://morning-rain-5c30.aruntailor635.workers.dev')

# Global Headers for web requests
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==========================================
# 1. SETUP FLASK SERVER FOR RENDER PORT BINDING
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Eternity is online, glowing, and protecting the faction 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Background thread starts Flask before bot connection
server_thread = Thread(target=run_web_server, daemon=True)
server_thread.start()

# ==========================================
# 2. LOAD ENVIRONMENT VARIABLES & CONFIG
# ==========================================
DISCORD_TOKEN = os.getenv('ETERNITY_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
OWNER_ID = int(os.getenv('OWNER_ID', 1477528681709830297))

API_KEYS = [
    os.getenv('GEMINI_API_KEY'),
    os.getenv('GEMINI_KEY_1'),
    os.getenv('GEMINI_KEY_2')
]
API_KEYS = [k for k in API_KEYS if k]

if not DISCORD_TOKEN:
    raise ValueError("ETERNITY_TOKEN must be set!")

if not API_KEYS:
    raise ValueError("At least one GEMINI key must be set!")

# ==========================================
# 3. INITIALIZE DISCORD BOT
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class EternityBot(commands.Bot):
    def __init__(self):
        # OVERRIDE DISCORD API BASE_URL VIA CLOUDFLARE PROXY
        http_options = {
            'base_url': WORKER_PROXY_URL
        }
        
        super().__init__(
            command_prefix='?', 
            intents=intents,
            http_options=http_options
        )
        
        self.SPECIAL_CHANNEL_ID = 1500095634588569600
        
        self.ADMIN_IDS = [1477528681709830297]
        self.MODERATOR_ROLE_ID = 1485660896746541259
        
        self.SYSTEM_PROMPT = faction_data.SYSTEM_PROMPT
        self.session = None
        self.db_client = None
        self.db = None
        self.profiles = None
        
        self.conversation_history = {}
        self.chat_cooldowns = {}

    async def setup_hook(self):
        self.session = aiohttp.ClientSession(headers=DEFAULT_HEADERS)
        
        if not MONGO_URI:
            print("⚠️ WARNING: MONGO_URI environment variable is missing!")
        else:
            try:
                self.db_client = motor.motor_asyncio.AsyncIOMotorClient(
                    MONGO_URI,
                    tlsCAFile=certifi.where()
                )
                self.db = self.db_client["eternal_faction_db"]
                self.profiles = self.db["user_profiles"]
                print("🛰️ MongoDB Atlas Pipeline: Connected to ClusterEternal successfully!")
            except Exception as e:
                print(f"MongoDB Async Error: {e}")

        initial_extensions = [
            'cogs.moderation',
            'cogs.reactions'
        ]
        
        if os.path.exists("cogs/utility.py"):
            initial_extensions.append('cogs.utility')
        elif os.path.exists("cogs/utilities.py"):
            initial_extensions.append('cogs.utilities')
            
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
                print(f"⚡ Extension '{extension}' loaded successfully!")
            except Exception as e:
                print(f"❌ Failed to load extension '{extension}': {e}")

    async def close(self):
        if self.session:
            await self.session.close()
        if self.db_client:
            self.db_client.close()
        await super().close()

    async def get_gemini_response(self, user_message: str, user_id: int, attachment_data=None) -> str:
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        combined_instructions = (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"Core Faction Knowledge Base:\n{faction_data.FACTION_PROMPT}"
        )

        if attachment_data:
            contents_payload = [user_message, attachment_data]
        else:
            self.conversation_history[user_id].append({"role": "user", "parts": [user_message]})
            if len(self.conversation_history[user_id]) > 15:
                self.conversation_history[user_id] = self.conversation_history[user_id][-15:]
            contents_payload = self.conversation_history[user_id]

        keys_to_try = API_KEYS.copy()
        random.shuffle(keys_to_try)

        # Aapke original model names
        models_to_attempt = [
            'models/gemini-3.6-flash',
            'models/gemini-3.5-flash-lite'
        ]

        for key in keys_to_try:
            genai.configure(api_key=key)
            for model_name in models_to_attempt:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=combined_instructions
                    )
                    
                    response = await asyncio.to_thread(
                        model.generate_content, contents_payload
                    )
                    assistant_message = response.text
                    
                    if not attachment_data:
                        self.conversation_history[user_id].append({"role": "model", "parts": [assistant_message]})
                    return assistant_message

                except Exception as e:
                    error_str = str(e)
                    print(f"Error on current API key ({model_name}): {error_str}")
                    
                    if "429" in error_str or "quota" in error_str.lower() or "resource_exhausted" in error_str.lower():
                        print(f"⚠️ Quota hit on {model_name}. Pausing for 3 seconds before fallback...")
                        await asyncio.sleep(3)
                        continue
                    else:
                        break
                    
        return "💠 *The cosmic frequencies are currently overloaded, my friends! Let the stars align and try again in a brief moment!*"

bot = EternityBot()

# Global Error Handler for Slash Commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandInvokeError):
        original = error.original
        if isinstance(original, discord.errors.HTTPException) and original.status == 429:
            print(f"⚠️ 429 Blocked on /{interaction.command.name}: Discord API rate limit hit.")
            return
    print(f"❌ Command Error in /{interaction.command.name}: {error}")

# ==========================================
# 4. BOT EVENTS & COMMANDS
# ==========================================
@bot.event
async def on_ready():
    print(f'✨ {bot.user.name} is fully online and active via Cloudflare Worker Proxy!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over Eternal"))

@bot.command(name='ping')
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"✨ Sparkling! Pong! My cosmic waves reached you in {latency}ms. Ready for action?")

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
        await ctx.send("🌐 Syncing clean commands globally...")
        try:
            synced = await bot.tree.sync()
            await ctx.send(f"✅ Synced **{len(synced)}** clean commands globally!")
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

# ==========================================
# MESSAGE EVENT HANDLING
# ==========================================
@bot.event
async def on_message(message):
    if message.author.bot or message.mention_everyone:
        return
    
    if message.guild is None:
        if message.author.id != OWNER_ID:
            try:
                await message.reply("🔒 Direct messages are disabled for AI processing. Please use the server channels!")
            except Exception:
                pass
            return
    
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return
    
    content_lower = message.content.lower()
    
    if "eternal" in content_lower or "victory" in content_lower:
        try:
            await message.add_reaction("💠")
        except Exception:
            pass

    is_gif = "tenor.com" in content_lower or "giphy.com" in content_lower
    if not is_gif and message.attachments:
        is_gif = any(att.filename.lower().endswith('.gif') for att in message.attachments)

    if content_lower == "protect the faction" or content_lower == "?cosmicgif":
        cosmic_gif_url = "https://tenor.com/view/nebula-galaxy-space-cosmic-universe-gif-22445853"
        await message.channel.send(cosmic_gif_url)
        return  
    
    is_pinged_or_replied = bot.user.mentioned_in(message)
    if not is_pinged_or_replied and message.reference:
        try:
            replied_to = await message.channel.fetch_message(message.reference.message_id)
            if replied_to.author == bot.user:
                is_pinged_or_replied = True
        except Exception:
            pass

    name_called = "eternity" in content_lower
    should_reply = (message.channel.id == bot.SPECIAL_CHANNEL_ID) or is_pinged_or_replied or name_called

    if should_reply:
        current_time = time.time()
        user_id = message.author.id
        if user_id in bot.chat_cooldowns:
            elapsed = current_time - bot.chat_cooldowns[user_id]
            if elapsed < 5:
                remaining = int(5 - elapsed)
                try:
                    await message.reply(f"⏰ *Hold your energy, guardian! The cosmic core is cooling down. Wait {remaining}s.*", delete_after=3)
                except Exception:
                    pass
                return
        
        bot.chat_cooldowns[user_id] = current_time

        try:
            async with message.channel.typing():
                clean_message = message.content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
                
                if not clean_message and is_gif:
                    clean_message = "Scan this GIF asset I sent you!"
                elif not clean_message and message.attachments:
                    clean_message = "Scan this asset!"
                
                if clean_message:
                    attachment_data = None
                    if message.attachments and bot.session:
                        try:
                            file_attachment = message.attachments[0]
                            if file_attachment.content_type:
                                async with bot.session.get(file_attachment.url) as resp:
                                    if resp.status == 200:
                                        file_bytes = await resp.read()
                                        attachment_data = {
                                            'mime_type': file_attachment.content_type,
                                            'data': file_bytes
                                        }
                        except Exception as err:
                            print(f"Vision direct parse warning: {err}")
                    
                    response = await bot.get_gemini_response(clean_message, message.author.id, attachment_data)
                    
                    if len(response) > 2000:
                        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                        for chunk in chunks:
                            await message.reply(chunk, mention_author=False)
                    else:
                        await message.reply(response, mention_author=False)
                else:
                    if not message.attachments:
                        await message.reply("✨ The incoming frequency appears empty!", mention_author=False)
        except discord.errors.HTTPException as typing_err:
            if typing_err.status == 429:
                print("⚠️ Typing indicator blocked by Discord rate limit (429). Skipped typing status.")

# Safe Gateway Connection Handling
if __name__ == "__main__":
    print("🚀 Connecting Eternity Gateway via Cloudflare Worker Proxy...")
    try:
        bot.run(DISCORD_TOKEN)
    except discord.errors.HTTPException as e:
        if e.status == 429:
            print("⚠️ DISCORD 429 RATE LIMIT ENCOUNTERED! Pausing process for 120s...")
            time.sleep(120)
        sys.exit(1)
    except Exception as e:
        print(f"❌ ETERNITY LAUNCH CRASH: {e}")
        sys.exit(1)
                

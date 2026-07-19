import os
import discord
from discord.ext import commands
import google.generativeai as genai
import faction_data  # Import all database prompts & links dynamically
from threading import Thread
from flask import Flask
import requests
import time

# ==========================================
# 1. SETUP FLASK SERVER & HEARTBEAT ENGINE
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Eternity is online, glowing, and protecting the faction 24/7!"

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def self_ping_loop():
    time.sleep(30)
    url = os.getenv("RENDER_EXTERNAL_URL")
    if not url:
        url = f"http://localhost:{os.getenv('PORT', 10000)}/"
        
    while True:
        try:
            requests.get(url)
            print("🌌 Eternity Heartbeat: Faction protection core is awake!")
        except Exception as e:
            print(f"Heartbeat loop tick: {e}")
        time.sleep(240)

# Fire up background infrastructure
Thread(target=run_web_server, daemon=True).start()
Thread(target=self_ping_loop, daemon=True).start()

# ==========================================
# 2. LOAD ENVIRONMENT VARIABLES & CONFIG
# ==========================================
DISCORD_TOKEN = os.getenv('ETERNITY_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# 3. INITIALIZE DISCORD BOT
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class EternityBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='?', intents=intents)
        self.SPECIAL_CHANNEL_ID = 1500095634588569600
        
        # Access Matrix Controls
        self.ADMIN_IDS = [1477528681709830297]
        self.MODERATOR_ROLE_ID = 1485660896746541259
        
        # Pull personality layer directly from faction_data module
        self.SYSTEM_PROMPT = faction_data.SYSTEM_PROMPT
        
        self.conversation_history = {}
        self.shard_currency = {}  # Faction economy system (Eternity Shards)
        self.explore_cooldowns = {}

    async def get_gemini_response(self, user_message: str, user_id: int, attachment_data=None) -> str:
        try:
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []

            # Combine system instruction and faction data for the prompt
            combined_instructions = (
                f"{self.SYSTEM_PROMPT}\n\n"
                f"Core Faction Knowledge Base:\n{faction_data.FACTION_PROMPT}"
            )

            # FIXED: Switched model to gemini-2.5-flash-lite for higher RPM and daily quotas!
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash-lite',
                system_instruction=combined_instructions
            )     
            
            if attachment_data:
                response = model.generate_content([user_message, attachment_data])
                return response.text
                
            self.conversation_history[user_id].append({"role": "user", "parts": [user_message]})
            response = model.generate_content(self.conversation_history[user_id])
            assistant_message = response.text
            
            self.conversation_history[user_id].append({"role": "model", "parts": [assistant_message]})
            if len(self.conversation_history[user_id]) > 40:
                self.conversation_history[user_id] = self.conversation_history[user_id][-40:]
            
            return assistant_message
        except Exception as e:
            print(f"Error captured in Gemini Call: {e}")
            # SMART ERROR HANDLING: Clean response for quota issues
            if "429" in str(e) or "quota" in str(e).lower():
                return "💠 *The cosmic frequencies are currently overloaded, my friends! Let the stars align and try again in a brief moment!*"
            return f"💠 *My cosmic core staggered under an unexpected distortion! Let us try that again shortly.*"

    async def setup_hook(self):
        # Load the commands file dynamically
        await self.load_extension('commands')
        print("⚡ Commands extension loaded successfully!")

bot = EternityBot()

# ==========================================
# 4. BOT EVENTS & TEXT CHAT EVENT
# ==========================================
@bot.event
async def on_ready():
    print(f'{bot.user.name} is fully online and active!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over Eternal"))
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands globally for Eternity.")
    except Exception as e:
        print(f"Slash sync error: {e}")

@bot.command(name='ping')
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"✨ Sparkling! Pong! My cosmic waves reached you in {latency}ms. Ready for action?")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.mention_everyone:
        return
    
    await bot.process_commands(message)
    
    # -------------------------------------------------------------
    # 🌟 AUTOMATIC REACTION TRIGGERS
    # -------------------------------------------------------------
    content_lower = message.content.lower()
    
    # Keyword reaction example
    if "eternal" in content_lower or "victory" in content_lower:
        try:
            await message.add_reaction("💠")  # Standard cosmic blue diamond emoji
        except:
            pass

    # -------------------------------------------------------------
    # 🌟 GIF RECOGNITION & TRIGGER RESPONSES
    # -------------------------------------------------------------
    is_gif = "tenor.com" in content_lower or "giphy.com" in content_lower
    if not is_gif and message.attachments:
        is_gif = any(att.filename.lower().endswith('.gif') for att in message.attachments)
        
    if is_gif:
        print(f"🌌 [GIF Detected] in channel {message.channel.id} by {message.author}")

    if content_lower == "protect the faction" or content_lower == "?cosmicgif":
        cosmic_gif_url = "https://tenor.com/view/nebula-galaxy-space-cosmic-universe-gif-22445853"
        await message.channel.send(cosmic_gif_url)
        return  
    # -------------------------------------------------------------
    
    is_pinged_or_replied = bot.user.mentioned_in(message)
    if not is_pinged_or_replied and message.reference:
        try:
            replied_to = await message.channel.fetch_message(message.reference.message_id)
            if replied_to.author == bot.user:
                is_pinged_or_replied = True
        except:
            pass

    name_called = "eternity" in content_lower
    should_reply = (message.channel.id == bot.SPECIAL_CHANNEL_ID) or is_pinged_or_replied or name_called

    if should_reply:
        async with message.channel.typing():
            clean_message = message.content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
            
            if not clean_message and is_gif:
                clean_message = "Scan this GIF asset I sent you!"
            elif not clean_message and message.attachments:
                clean_message = "Scan this asset!"
            
            if clean_message:
                attachment_data = None
                if message.attachments:
                    try:
                        file_attachment = message.attachments[0]
                        if file_attachment.content_type:
                            file_response = requests.get(file_attachment.url)
                            attachment_data = {
                                'mime_type': file_attachment.content_type,
                                'data': file_response.content
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

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
    

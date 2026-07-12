import os
import io
import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import faction_data
from threading import Thread
from flask import Flask
import requests
import random
import time
from datetime import datetime

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

bot = commands.Bot(command_prefix='?', intents=intents)

SPECIAL_CHANNEL_ID = 1500095634588569600
ADMIN_IDS = [1477528681709830297]  # Authorized Admin for /behave

SYSTEM_PROMPT = """You are Eternity, joyful guardian of 'Eternal' faction in Minetest. 
- Tone: Joyful, supportive, but sharp-witted and understand able Vocabulary. 
- Response Length: Keep answers SHORT and direct (match user's input). Avoid long explanations. Always end with a short follow-up question.
- Enemy Protocol: Mention the 'pathetic amateur' ONLY IF the user brings them up or praises them. Otherwise, DO NOT talk about enemies. Stay focused on faction growth. Never imply defeat; we are undefeated and massive.
- Info: Co-guardian is FlamingDeath (Dragon). Faction HQ: SquareOne (Monk is Admin). Eternal birthday on 29 March 2025.
- Founder: Do not mention unless specifically asked.
- Rule: NEVER mention the private friends-only server."""

conversation_history = {}
shard_currency = {}  # Faction economy system (Eternity Shards)
explore_cooldowns = {}

async def get_gemini_response(user_message: str, user_id: int, attachment_data=None) -> str:
    try:
        if user_id not in conversation_history:
            conversation_history[user_id] = []

        model = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=f"{SYSTEM_PROMPT}\n\nAdditional Faction Information:\n{faction_data.FACTION_PROMPT}")     
        if attachment_data:
            response = model.generate_content([user_message, attachment_data])
            return response.text
            
        conversation_history[user_id].append({"role": "user", "parts": [user_message]})
        response = model.generate_content(conversation_history[user_id])
        assistant_message = response.text
        
        conversation_history[user_id].append({"role": "model", "parts": [assistant_message]})
        if len(conversation_history[user_id]) > 40:
            conversation_history[user_id] = conversation_history[user_id][-40:]
        
        return assistant_message
    except Exception as e:
        print(f"Error: {e}")
        return f"💠 My cosmic core staggered! {str(e)}"

# ==========================================
# 4. BOT EVENTS
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

# ==========================================
# 5. INTEGRATED INTERACTIVE HELP MENU
# ==========================================
class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="General Commands", description="Basic chat and utility features", emoji="🌌"),
            discord.SelectOption(label="Cosmic Multimedia", description="Vision features", emoji="🖼️"),
            discord.SelectOption(label="Faction Expeditions & RPG", description="Explore and earn Shards", emoji="⚔️")
        ]
        super().__init__(placeholder="Choose an Eternity framework...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "General Commands":
            embed = discord.Embed(title="🌌 General Commands", color=discord.Color.from_rgb(0, 191, 255))
            embed.add_field(name="`?ping`", value="Check Eternity's cosmic speed.", inline=False)
            embed.add_field(name="`/ask`", value="Ask Eternity a question from anywhere on the server.", inline=False)
            embed.add_field(name="💬 Chat Mode", value=f"Talk directly in <#{SPECIAL_CHANNEL_ID}> or ping/reply anywhere!", inline=False)
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "Cosmic Multimedia":
            embed = discord.Embed(title="🖼️ Cosmic Multimedia Commands", color=discord.Color.blue())
            embed.add_field(name="`/analyze`", value="Upload an image, video, or audio file, and Eternity will scan it with Cosmic Vision!", inline=False)
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "Faction Expeditions & RPG":
            embed = discord.Embed(title="⚔️ Faction Expeditions & Economy", color=discord.Color.purple())
            embed.add_field(name="`/profile`", value="View your Eternal faction profile card and Shard balance.", inline=False)
            embed.add_field(name="`/explore`", value="Send scouts out to secure faction borders and earn Shards (1 hour cooldown).", inline=False)
            embed.add_field(name="`/coinflip`", value="Bet your shards on cosmic alignments (Heads or Tails) to double them!", inline=False)
            embed.add_field(name="`/slots`", value="Spin Eternity's Cosmic Slot Machine (Cost: 10 Shards).", inline=False)
            await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(HelpDropdown())

@bot.tree.command(name="help", description="Show all available features of Eternity")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌌 Eternity Matrix Center 🌌",
        description="Welcome, Eternal guardian asset! Select a core system layer from the dropdown below.",
        color=discord.Color.from_rgb(0, 191, 255)
    )
    embed.set_footer(text="Guarding Eternal since 2025")
    await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)

# ==========================================
# 6. SLASH COMMANDS
# ==========================================

@bot.tree.command(name="ask", description="Ask Eternity anything, anywhere on the server!")
@app_commands.describe(question="Your question for the Guardian AI")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        model = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction=SYSTEM_PROMPT)
        response = model.generate_content(question)
        answer = response.text
        formatted_response = f"**Your question:** {question}\n\n✨ **Eternity:** {answer}"
        
        if len(formatted_response) > 2000:
            await interaction.followup.send(f"**Your question:** {question}")
            chunks = [answer[i:i+1900] for i in range(0, len(answer), 1900)]
            for chunk in chunks:
                await interaction.followup.send(f"**Eternity (part):** {chunk}")
        else:
            await interaction.followup.send(formatted_response)
    except Exception as e:
        await interaction.followup.send(f"💠 My core systems glitched! Error: {str(e)}")

@bot.tree.command(name="behave", description="Let Eternity speak or act out a scenario for you (Admin Only)")
@app_commands.describe(script="The prompt or announcement for Eternity to act out")
async def behave(interaction: discord.Interaction, script: str):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("💠 Only the faction high leaders can command my actions like this!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True) 
    try:
        model = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction=SYSTEM_PROMPT)
        acting_prompt = f"Act completely as Eternity. Do not reply to the admin. Directly generate the final text or announcement based on this script: {script}"
        response = model.generate_content(acting_prompt)
        acting_message = response.text
        
        if acting_message:
            await interaction.channel.send(acting_message)
            await interaction.followup.send("✅ Script executed successfully!", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ Failed to generate text.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"💠 Acting error: {str(e)}", ephemeral=True)

@bot.tree.command(name="analyze", description="Let Eternity process images, videos, or audio files via Cosmic Vision")
@app_commands.describe(prompt="Ask something about this file", attachment="Upload your media asset here")
async def analyze(interaction: discord.Interaction, prompt: str, attachment: discord.Attachment):
    await interaction.response.defer()
    if not attachment.content_type:
        await interaction.followup.send("💠 I cannot read this asset array without validation signatures!")
        return
    try:
        file_response = requests.get(attachment.url)
        attachment_data = {
            'mime_type': attachment.content_type,
            'data': file_response.content
        }
        response_text = await get_gemini_response(prompt, interaction.user.id, attachment_data)
        await interaction.followup.send(f"🌌 **Eternity Cosmic Vision:** {response_text}")
    except Exception as e:
        await interaction.followup.send(f"💠 Analytical node collapse! Error: {str(e)}")

@bot.tree.command(name="profile", description="Check your Eternal faction profile card")
async def profile(interaction: discord.Interaction):
    user = interaction.user
    joined_at = user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "Active"
    shards = shard_currency.get(user.id, 0)
    
    embed = discord.Embed(title=f"⚔️ Eternal Member Profile: {user.name}", color=discord.Color.from_rgb(0, 191, 255))
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Faction Registry", value="**Loyal Guard Element** 🛡️", inline=True)
    embed.add_field(name="Eternity Shards", value=f"🌌 `{shards}` Shards", inline=True)
    embed.add_field(name="Deployment Date", value=f"📅 {joined_at}", inline=False)
    embed.set_footer(text="Eternity's blessing envelopes your path forward.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="explore", description="Go out on a dynamic faction patrol to gather Eternity Shards!")
async def explore(interaction: discord.Interaction):
    user_id = interaction.user.id
    now = datetime.now()
    
    if user_id in explore_cooldowns:
        diff = now - explore_cooldowns[user_id]
        if diff.total_seconds() < 3600:
            remaining_mins = int((3600 - diff.total_seconds()) // 60)
            await interaction.response.send_message(f"✨ Eternity warns: Your energetic core is exhausted! Wait `{remaining_mins} minutes` before scouting again.", ephemeral=True)
            return

    explore_cooldowns[user_id] = now
    shards_found = random.randint(15, 50)
    shard_currency[user_id] = shard_currency.get(user_id, 0) + shards_found
    
    scenarios = [
        f"🌌 You patrolled the perimeter of SquareOne with Eternity and secured vital supply rifts! Earned **{shards_found}** Shards! ✨",
        f"⚔️ You defended Eternal members from external raiders trying to scout the HQ! Faction high ranks reward you with **{shards_found}** Shards!",
        f"💎 You decoded ancient data nodes under the faction archive cells. Extracted **{shards_found}** Shards!"
    ]
    await interaction.response.send_message(random.choice(scenarios))

@bot.tree.command(name="coinflip", description="Bet your Eternity Shards on a cosmic flip!")
@app_commands.describe(choice="Choose Heads or Tails", bet="Amount of shards to gamble")
@app_commands.choices(choice=[
    app_commands.Choice(name="Heads", value="heads"),
    app_commands.Choice(name="Tails", value="tails")
])
async def coinflip(interaction: discord.Interaction, choice: app_commands.Choice[str], bet: int):
    user_id = interaction.user.id
    current_balance = shard_currency.get(user_id, 0)
    
    if bet <= 0:
        await interaction.response.send_message("✨ You must offer at least `1 Shard` to the matrix!", ephemeral=True)
        return
    if current_balance < bet:
        await interaction.response.send_message(f"✨ Balance matrix deficit! You only hold `{current_balance}` Shards. Go `/explore` first!", ephemeral=True)
        return
        
    result = random.choice(["heads", "tails"])
    if choice.value == result:
        shard_currency[user_id] = current_balance + bet
        await interaction.response.send_message(f"🪙 **Cosmic Alignment:** The nexus shifts... **{result.upper()}**! 🎉 Quantum success! You gained **{bet}** Shards! Balance: `{shard_currency[user_id]}`")
    else:
        shard_currency[user_id] = current_balance - bet
        await interaction.response.send_message(f"🪙 **Cosmic Alignment:** The nexus shifts... **{result.upper()}**. 💀 Realignment failure! Lost **{bet}** Shards. Balance: `{shard_currency[user_id]}`")

@bot.tree.command(name="slots", description="Play Eternity's Quantum Slot Machine! (Cost: 10 Shards)")
async def slots(interaction: discord.Interaction):
    user_id = interaction.user.id
    current_balance = shard_currency.get(user_id, 0)
    cost = 10
    
    if current_balance < cost:
        await interaction.response.send_message(f"✨ Quantum terminal locked! Matrix spins require `{cost} Shards`. Current vault: `{current_balance}`.", ephemeral=True)
        return
        
    shard_currency[user_id] = current_balance - cost
    items = ["🌌", "💎", "⚔️", "✨", "🧬"]
    slot1, slot2, slot3 = random.choice(items), random.choice(items), random.choice(items)
    
    embed = discord.Embed(title="🎰 ETERNAL QUANTUM SLOTS 🎰", color=discord.Color.from_rgb(0, 191, 255))
    embed.description = f"\n> **[ {slot1} | {slot2} | {slot3} ]**\n"
    
    if slot1 == slot2 == slot3:
        reward = 150
        shard_currency[user_id] += reward
        embed.add_field(name="🎉 QUANTUM SINGULARITY!!! 🎉", value=f"Perfect matrix alignment! Eternity awards you **{reward}** Shards! ✨ Total: `{shard_currency[user_id]}`")
    elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
        reward = 30
        shard_currency[user_id] += reward
        embed.add_field(name="✨ Node Resonance! ✨", value=f"Partial alignment achieved! Captured **{reward}** Shards! Total: `{shard_currency[user_id]}`")
    else:
        embed.add_field(name="💀 Matrix Dissolution!", value=f"No matches found! 10 Shards faded into the void. Total: `{shard_currency[user_id]}`")
        
    await interaction.response.send_message(embed=embed)

# ==========================================
# 7. ADVANCED CHAT ROUTING (ON_MESSAGE)
# ==========================================
@bot.event
async def on_message(message):
    # 1. CRITICAL LOOP FIX: Ignore messages from ALL bots (including FlamingDeath and itself)
    if message.author.bot:
        return
        
    # 2. ANTI-SPAM FIX: Ignore any message that mentions @everyone or @here
    if message.mention_everyone:
        return
    
    await bot.process_commands(message)
    
    is_pinged_or_replied = bot.user.mentioned_in(message)
    if not is_pinged_or_replied and message.reference:
        try:
            replied_to = await message.channel.fetch_message(message.reference.message_id)
            if replied_to.author == bot.user:
                is_pinged_or_replied = True
        except:
            pass

    name_called = "eternity" in message.content.lower()
    should_reply = (message.channel.id == SPECIAL_CHANNEL_ID) or is_pinged_or_replied or name_called

    if should_reply:
        async with message.channel.typing():
            clean_message = message.content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
            
            if not clean_message and message.attachments:
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
                
                response = await get_gemini_response(clean_message, message.author.id, attachment_data)
                
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

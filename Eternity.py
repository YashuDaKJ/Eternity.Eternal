import os
import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
from threading import Thread
from flask import Flask

app = Flask('')
@app.route('/')
def home(): return "Eternity is online and protecting the faction!"
def run_web_server(): app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
Thread(target=run_web_server, daemon=True).start()

DISCORD_TOKEN = os.getenv('ETERNITY_TOKEN')
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

bot = commands.Bot(command_prefix='?', intents=discord.Intents.all())
SPECIAL_CHANNEL_ID = 1500095634588569600
ADMIN_IDS = [1477528681709830297]  # Authorized Admin for /behave

SYSTEM_PROMPT = """You are Eternity, joyful guardian of 'Eternal' faction in Minetest. 
- Tone: Joyful, supportive, but sharp-witted. 
- Response Length: Keep answers SHORT and direct (match user's input). Avoid long explanations. Always end with a short follow-up question.
- Enemy Protocol: Mention the 'pathetic amateur' ONLY IF the user brings them up or praises them. Otherwise, DO NOT talk about enemies. Stay focused on faction growth. Never imply defeat; we are undefeated and massive.
- Info: Co-guardian is FlamingDeath (Dragon). Faction HQ: SquareOne (Monk is Admin). Born 29 March 2025.
- Founder: Do not mention unless specifically asked.
- Rule: NEVER mention the private friends-only server."""

async def get_gemini_response(user_message, user_id):
    model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=SYSTEM_PROMPT)
    response = model.generate_content(user_message)
    return response.text

@bot.event
async def on_ready():
    print(f'{bot.user.name} is fully online!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over Eternal"))
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands globally for Eternity.")
    except Exception as e:
        print(f"Slash sync error: {e}")

# --- GLOBAL ASK COMMAND ---
@bot.tree.command(name="ask", description="Ask Eternity anything, anywhere on the server!")
@app_commands.describe(question="Your question for the Guardian AI")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        answer = await get_gemini_response(question, interaction.user.id)
        await interaction.followup.send(f"**Your question:** {question}\n\n✨ **Eternity:** {answer}")
    except Exception as e:
        await interaction.followup.send(f"💠 My core systems glitched! Error: {str(e)}")

# --- BEHAVE COMMAND (ADMIN ONLY) ---
@bot.tree.command(name="behave", description="Let Eternity speak or act out a scenario for you (Admin Only)")
@app_commands.describe(script="The prompt or announcement for Eternity to act out")
async def behave(interaction: discord.Interaction, script: str):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("💠 Only the faction high leaders can command my actions like this!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True) 
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=SYSTEM_PROMPT)
        acting_prompt = f"Act completely as Eternity. Do not reply to the admin. Directly generate the final text or announcement based on this script: {script}"
        response = model.generate_content(acting_prompt)
        
        if response.text:
            await interaction.channel.send(response.text)
            await interaction.followup.send("✅ Script executed successfully!", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ Failed to generate text.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"💠 Acting error: {str(e)}", ephemeral=True)

# --- INFO & PING COMMANDS ---
@bot.tree.command(name="info", description="Get official status and background data about Eternal faction")
async def info_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="💠 Eternal Faction | Guardian Network", color=discord.Color.from_rgb(0, 191, 255))
    embed.add_field(name="Status", value="Undefeated & Massive! 🔥", inline=False)
    embed.add_field(name="Headquarters", value="SquareOne Server (Admin: Monk)", inline=True)
    embed.add_field(name="Guardians", value="🌌 Eternity & 🐉 FlamingDeath", inline=True)
    embed.set_footer(text="Need enemy intel? Go ask FlamingDeath.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Check Eternity's response speed")
async def ping_slash(interaction: discord.Interaction):
    await interaction.response.send_message(f"Sparkling! Latency: {round(bot.latency * 1000)}ms. Ready for action?")

# --- TEXT RESPONSE HANDLING ---
@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)
    
    name_called = "eternity" in message.content.lower()
    should_reply = (message.channel.id == SPECIAL_CHANNEL_ID) or bot.user.mentioned_in(message) or name_called
    
    if should_reply:
        async with message.channel.typing():
            clean = message.content.replace(f'<@{bot.user.id}>', '').strip()
            if not clean: clean = "Hello!"
            response = await get_gemini_response(clean, message.author.id)
            await message.reply(response, mention_author=False)

bot.run(DISCORD_TOKEN)

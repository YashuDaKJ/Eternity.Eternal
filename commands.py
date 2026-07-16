import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import random
import requests
from datetime import datetime

class EternityCommands(commands.GroupCog if False else commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Dropdown interactive logic
    class HelpDropdown(discord.ui.Select):
        def __init__(self, special_channel_id):
            self.special_channel_id = special_channel_id
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
                embed.add_field(name="💬 Chat Mode", value=f"Talk directly in <#{self.special_channel_id}> or ping/reply anywhere!", inline=False)
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
        def __init__(self, special_channel_id):
            super().__init__()
            self.add_item(EternityCommands.HelpDropdown(special_channel_id))

    @app_commands.command(name="help", description="Show all available features of Eternity")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌌 Eternity Matrix Center 🌌",
            description="Welcome, Eternal guardian asset! Select a core system layer from the dropdown below.",
            color=discord.Color.from_rgb(0, 191, 255)
        )
        embed.set_footer(text="Guarding Eternal since 2025")
        await interaction.response.send_message(embed=embed, view=self.HelpView(self.bot.SPECIAL_CHANNEL_ID), ephemeral=True)

    @app_commands.command(name="ask", description="Ask Eternity anything, anywhere on the server!")
    @app_commands.describe(question="Your question for the Guardian AI")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        try:
            model = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction=self.bot.SYSTEM_PROMPT)
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

    @app_commands.command(name="behave", description="Let Eternity speak or act out a scenario for you (Admin Only)")
    @app_commands.describe(script="The prompt or announcement for Eternity to act out")
    async def behave(self, interaction: discord.Interaction, script: str):
        if interaction.user.id not in self.bot.ADMIN_IDS:
            await interaction.response.send_message("💠 Only the faction high leaders can command my actions like this!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True) 
        try:
            model = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction=self.bot.SYSTEM_PROMPT)
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

    @app_commands.command(name="analyze", description="Let Eternity process images, videos, or audio files via Cosmic Vision")
    @app_commands.describe(prompt="Ask something about this file", attachment="Upload your media asset here")
    async def analyze(self, interaction: discord.Interaction, prompt: str, attachment: discord.Attachment):
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
            response_text = await self.bot.get_gemini_response(prompt, interaction.user.id, attachment_data)
            await interaction.followup.send(f"🌌 **Eternity Cosmic Vision:** {response_text}")
        except Exception as e:
            await interaction.followup.send(f"💠 Analytical node collapse! Error: {str(e)}")

    @app_commands.command(name="profile", description="Check your Eternal faction profile card")
    async def profile(self, interaction: discord.Interaction):
        user = interaction.user
        joined_at = user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "Active"
        shards = self.bot.shard_currency.get(user.id, 0)
        
        embed = discord.Embed(title=f"⚔️ Eternal Member Profile: {user.name}", color=discord.Color.from_rgb(0, 191, 255))
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Faction Registry", value="**Loyal Guard Element** 🛡️", inline=True)
        embed.add_field(name="Eternity Shards", value=f"🌌 `{shards}` Shards", inline=True)
        embed.add_field(name="Deployment Date", value=f"📅 {joined_at}", inline=False)
        embed.set_footer(text="Eternity's blessing envelopes your path forward.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="explore", description="Go out on a dynamic faction patrol to gather Eternity Shards!")
    async def explore(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now()
        
        if user_id in self.bot.explore_cooldowns:
            diff = now - self.bot.explore_cooldowns[user_id]
            if diff.total_seconds() < 3600:
                remaining_mins = int((3600 - diff.total_seconds()) // 60)
                await interaction.response.send_message(f"✨ Eternity warns: Your energetic core is exhausted! Wait `{remaining_mins} minutes` before scouting again.", ephemeral=True)
                return

        self.bot.explore_cooldowns[user_id] = now
        shards_found = random.randint(15, 50)
        self.bot.shard_currency[user_id] = self.bot.shard_currency.get(user_id, 0) + shards_found
        
        scenarios = [
            f"🌌 You patrolled the perimeter of SquareOne with Eternity and secured vital supply rifts! Earned **{shards_found}** Shards! ✨",
            f"⚔️ You defended Eternal members from external raiders trying to scout the HQ! Faction high ranks reward you with **{shards_found}** Shards!",
            f"💎 You decoded ancient data nodes under the faction archive cells. Extracted **{shards_found}** Shards!"
        ]
        await interaction.response.send_message(random.choice(scenarios))

    @app_commands.command(name="coinflip", description="Bet your Eternity Shards on a cosmic flip!")
    @app_commands.describe(choice="Choose Heads or Tails", bet="Amount of shards to gamble")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, choice: app_commands.Choice[str], bet: int):
        user_id = interaction.user.id
        current_balance = self.bot.shard_currency.get(user_id, 0)
        
        if bet <= 0:
            await interaction.response.send_message("✨ You must offer at least `1 Shard` to the matrix!", ephemeral=True)
            return
        if current_balance < bet:
            await interaction.response.send_message(f"✨ Balance matrix deficit! You only hold `{current_balance}` Shards. Go `/explore` first!", ephemeral=True)
            return
            
        result = random.choice(["heads", "tails"])
        if choice.value == result:
            self.bot.shard_currency[user_id] = current_balance + bet
            await interaction.response.send_message(f"🪙 **Cosmic Alignment:** The nexus shifts... **{result.upper()}**! 🎉 Quantum success! You gained **{bet}** Shards! Balance: `{self.bot.shard_currency[user_id]}`")
        else:
            self.bot.shard_currency[user_id] = current_balance - bet
            await interaction.response.send_message(f"🪙 **Cosmic Alignment:** The nexus shifts... **{result.upper()}**. 💀 Realignment failure! Lost **{bet}** Shards. Balance: `{self.bot.shard_currency[user_id]}`")

    @app_commands.command(name="slots", description="Play Eternity's Quantum Slot Machine! (Cost: 10 Shards)")
    async def slots(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        current_balance = self.bot.shard_currency.get(user_id, 0)
        cost = 10
        
        if current_balance < cost:
            await interaction.response.send_message(f"✨ Quantum terminal locked! Matrix spins require `{cost} Shards`. Current vault: `{current_balance}`.", ephemeral=True)
            return
            
        self.bot.shard_currency[user_id] = current_balance - cost
        items = ["🌌", "💎", "⚔️", "✨", "🧬"]
        slot1, slot2, slot3 = random.choice(items), random.choice(items), random.choice(items)
        
        embed = discord.Embed(title="🎰 ETERNAL QUANTUM SLOTS 🎰", color=discord.Color.from_rgb(0, 191, 255))
        embed.description = f"\n> **[ {slot1} | {slot2} | {slot3} ]**\n"
        
        if slot1 == slot2 == slot3:
            reward = 150
            self.bot.shard_currency[user_id] += reward
            embed.add_field(name="🎉 QUANTUM SINGULARITY!!! 🎉", value=f"Perfect matrix alignment! Eternity awards you **{reward}** Shards! ✨ Total: `{self.bot.shard_currency[user_id]}`")
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            reward = 30
            self.bot.shard_currency[user_id] += reward
            embed.add_field(name="✨ Node Resonance! ✨", value=f"Partial alignment achieved! Captured **{reward}** Shards! Total: `{self.bot.shard_currency[user_id]}`")
        else:
            embed.add_field(name="💀 Matrix Dissolution!", value=f"No matches found! 10 Shards faded into the void. Total: `{self.bot.shard_currency[user_id]}`")
            
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EternityCommands(bot))
      

import discord
from discord.ext import commands

class Reactions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages and @everyone/@here pings
        if message.author.bot or message.mention_everyone:
            return

        content_lower = message.content.lower()

        # -------------------------------------------------------------
        # 🌟 AUTOMATIC REACTION TRIGGERS
        # -------------------------------------------------------------
        if "eternal" in content_lower or "victory" in content_lower:
            try:
                await message.add_reaction("💠")
            except discord.HTTPException:
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

async def setup(bot):
    await bot.add_cog(Reactions(bot))

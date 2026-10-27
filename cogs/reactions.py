import discord
from discord.ext import commands


class Reactions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.mention_everyone:
            return

        content_lower = message.content.lower()

        if "eternal" in content_lower or "victory" in content_lower:
            try:
                await message.add_reaction("💠")
            except discord.HTTPException:
                pass

        if content_lower in ("protect the faction", "?cosmicgif"):
            await message.channel.send("https://tenor.com/view/nebula-galaxy-space-cosmic-universe-gif-22445853")


async def setup(bot):
    await bot.add_cog(Reactions(bot))

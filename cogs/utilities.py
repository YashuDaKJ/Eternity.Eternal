import discord
from discord.ext import commands
from discord import app_commands


class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Core Utilities", description="AI, info and status commands", emoji="🌌"),
            discord.SelectOption(label="Moderation Vectors", description="Commands for faction order", emoji="🛡️"),
        ]
        super().__init__(placeholder="Select a module...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Core Utilities":
            embed = discord.Embed(title="🌌 Core Utilities", color=discord.Color.from_rgb(0, 191, 255))
            embed.add_field(name="`/ask`", value="Ask the AI anything.", inline=False)
            embed.add_field(name="`/userinfo`", value="Details about a member.", inline=False)
            embed.add_field(name="`/avatar`", value="Fetch a member's avatar.", inline=False)
            embed.add_field(name="`/afk`", value="Set your away status (removed when you talk).", inline=False)
            embed.add_field(name="`/report`", value="Report a member to the moderators.", inline=False)
        else:
            embed = discord.Embed(title="🛡️ Moderation", color=discord.Color.red())
            embed.add_field(name="`/warn` `/warnings`", value="Warn a member / view their warning history.", inline=False)
            embed.add_field(name="`/timeout` `/unmute`", value="Mute a member / lift the mute.", inline=False)
            embed.add_field(name="`/kick` `/ban` `/unban`", value="Remove or restore members.", inline=False)
            embed.add_field(name="`/clear`", value="Delete recent messages.", inline=False)
            embed.add_field(name="`/behave`", value="Send a conduct reminder.", inline=False)
            embed.add_field(name="`/add_log` `/search_logs` `/browse_categories`", value="Records database.", inline=False)
            embed.add_field(name="`/setlogchannel`", value="Admin: choose where logs and reports go.", inline=False)
        await interaction.response.edit_message(embed=embed)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown())


class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _is_authorized(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False
        if interaction.user.id in self.bot.ADMIN_IDS:
            return True
        return any(r.id == self.bot.MODERATOR_ROLE_ID for r in getattr(interaction.user, "roles", []))

    @app_commands.command(name="help", description="Show the Eternity command directory")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌌 Eternity Operations & Moderation System 🌌",
            description="Select a module from the dropdown to see its commands.",
            color=discord.Color.from_rgb(0, 191, 255),
        )
        await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)

    @app_commands.command(name="ask", description="Ask Eternity anything")
    @app_commands.describe(question="Your question")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        try:
            answer = await self.bot.get_gemini_response(question, interaction.user.id)
        except Exception as e:
            print(f"/ask failed: {e}", flush=True)
            return await interaction.followup.send("💠 *The cosmic frequencies are overloaded. Try again shortly!*")

        formatted = f"**Input Query:** {question}\n\n✨ **Eternity Output:** {answer}"
        if len(formatted) > 2000:
            await interaction.followup.send(f"**Input Query:** {question}"[:2000])
            for i in range(0, len(answer), 1900):
                await interaction.followup.send(answer[i:i + 1900])
        else:
            await interaction.followup.send(formatted)

    @app_commands.command(name="behave", description="Send a conduct reminder to a member")
    @app_commands.guild_only()
    @app_commands.describe(target="Member to remind", rule="Rule or behavior standard")
    async def behave(self, interaction: discord.Interaction, target: discord.Member,
                     rule: str = "Standard conduct & decorum."):
        if not self._is_authorized(interaction):
            return await interaction.response.send_message("❌ You lack the rights for this command.", ephemeral=True)
        embed = discord.Embed(
            title="⚠️ Conduct Reminder",
            description=f"Attention {target.mention}, please adjust your conduct to keep order.",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Directed To", value=target.mention, inline=True)
        embed.add_field(name="Issued By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Rule", value=rule[:1000], inline=False)
        embed.set_footer(text="Failure to comply may result in warnings or timeouts.")
        await interaction.response.send_message(content=target.mention, embed=embed,
                                                allowed_mentions=discord.AllowedMentions(users=[target]))

    @ask.error
    async def ask_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏰ *Cooling down. Try again in {error.retry_after:.1f}s.*"
        else:
            print(f"/ask error: {error!r}", flush=True)
            msg = "💠 Something went wrong. Try again shortly."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Utilities(bot))

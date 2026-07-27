import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta

# ==========================================
# MODERATION COG MODULE
# ==========================================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _is_authorized(self, interaction: discord.Interaction) -> bool:
        """Validates if user is Admin or Moderator Role holder."""
        if interaction.user.id in self.bot.ADMIN_IDS:
            return True
        if any(role.id == self.bot.MODERATOR_ROLE_ID for role in interaction.user.roles):
            return True
        return False

    @app_commands.command(name="warn", description="Issues a formal protocol infraction warning to a target member")
    @app_commands.describe(target="The user node receiving the warning infraction", reason="Reason for issuing the notice")
    async def warn(self, interaction: discord.Interaction, target: discord.Member, reason: str):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack administrative rights.", ephemeral=True)
            return

        if target.top_role >= interaction.user.top_role and interaction.user.id not in self.bot.ADMIN_IDS:
            await interaction.response.send_message("❌ Command execution denied: Insufficient hierarchy permissions.", ephemeral=True)
            return

        embed = discord.Embed(title="⚠️ Protocol Infraction Notice", color=discord.Color.red())
        embed.add_field(name="Target Element", value=target.mention, inline=True)
        embed.add_field(name="Issued By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Infraction Reason", value=reason, inline=False)
        embed.set_footer(text="Further violations will result in automatic containment protocols.")

        # Send warning notice only in the server channel, not via DM
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="timeout", description="Applies communication suppression matrix to an element (Mute)")
    @app_commands.describe(target="Target user node", minutes="Suppression duration in minutes", reason="Log input")
    async def timeout(self, interaction: discord.Interaction, target: discord.Member, minutes: int, reason: str = "Communication disruption."):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack administrative rights.", ephemeral=True)
            return

        if target.top_role >= interaction.user.top_role and interaction.user.id not in self.bot.ADMIN_IDS:
            await interaction.response.send_message("❌ Command execution denied: Insufficient hierarchy permissions.", ephemeral=True)
            return
        
        duration = timedelta(minutes=minutes)
        await target.timeout(duration, reason=reason)
        embed = discord.Embed(title="🔇 Communication Vector Suppressed", color=discord.Color.gold())
        embed.add_field(name="Target User", value=target.mention, inline=True)
        embed.add_field(name="Duration Vector", value=f"{minutes} Minutes", inline=True)
        embed.add_field(name="Reason Logged", value=reason, inline=False)
        
        # Send feedback only in the server channel, not via DM
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear", description="Purges a specific quantity of transmission frames from channel")
    @app_commands.describe(amount="Number of network message logs to erase")
    async def clear(self, interaction: discord.Interaction, amount: int):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack administrative rights.", ephemeral=True)
            return

        if amount <= 0 or amount > 100:
            await interaction.response.send_message("❌ Operational Error: Quantities must be between 1 and 100 entries.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ Operations Success: Purged `{len(deleted)}` historical message entries.", ephemeral=True)

    @app_commands.command(name="kick", description="Ejects a target member from the active server footprint")
    @app_commands.describe(target="The specific user node to kick", reason="Reason logging input")
    async def kick(self, interaction: discord.Interaction, target: discord.Member, reason: str = "Standard administrative mitigation."):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack administrative rights.", ephemeral=True)
            return

        if target.top_role >= interaction.user.top_role and interaction.user.id not in self.bot.ADMIN_IDS:
            await interaction.response.send_message("❌ Command execution denied: Insufficient hierarchy permissions.", ephemeral=True)
            return
        
        await target.kick(reason=reason)
        embed = discord.Embed(title="👢 Element Ejected", color=discord.Color.orange())
        embed.add_field(name="Target User", value=target.mention, inline=True)
        embed.add_field(name="Enforcement Action", value="Ejection (Kick)", inline=True)
        embed.add_field(name="Reason Logged", value=reason, inline=False)
        
        # Send feedback only in the server channel, not via DM
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ban", description="Terminates a member's network connection permanently")
    @app_commands.describe(target="The specific user node to ban", reason="Reason logging input")
    async def ban(self, interaction: discord.Interaction, target: discord.Member, reason: str = "Violation of standard protocol."):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack administrative rights.", ephemeral=True)
            return

        if target.top_role >= interaction.user.top_role and interaction.user.id not in self.bot.ADMIN_IDS:
            await interaction.response.send_message("❌ Command execution denied: Insufficient hierarchy permissions.", ephemeral=True)
            return
        
        await target.ban(reason=reason)
        embed = discord.Embed(title="🔨 Element Connection Terminated", color=discord.Color.red())
        embed.add_field(name="Target User", value=target.mention, inline=True)
        embed.add_field(name="Enforcement Action", value="Permanent Ban", inline=True)
        embed.add_field(name="Reason Logged", value=reason, inline=False)
        
        # Send feedback only in the server channel, not via DM
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unban", description="Restores server connection rights to a previously banned ID")
    @app_commands.describe(user_id="The exact digital ID string of the target user", reason="Reason logging input")
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "Sanction period expired."):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack administrative rights.", ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=reason)
            embed = discord.Embed(title="🔓 Element Clearance Restored", color=discord.Color.green())
            embed.add_field(name="Target User", value=user.name, inline=True)
            embed.add_field(name="Status Matrix", value="Restored", inline=True)
            embed.add_field(name="Reason Logged", value=reason, inline=False)
            
            # Send feedback only in the server channel, not via DM
            await interaction.response.send_message(embed=embed)
        except discord.NotFound:
            await interaction.response.send_message("❌ Execution Error: Specified user ID could not be resolved.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Systems Error: Unban protocol failed: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))

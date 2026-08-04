import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta

# ==========================================
# ETERNITY SECURITY & MODERATION COG
# ==========================================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _is_authorized(self, interaction: discord.Interaction) -> bool:
        """Validates if user is Admin or Moderator Role holder."""
        if interaction.user.id in self.bot.ADMIN_IDS:
            return True
        if any(role.id == getattr(self.bot, 'MODERATOR_ROLE_ID', None) for role in interaction.user.roles):
            return True
        return False

    # ==========================================
    # ADMIN EXCLUSIVE COVERT COPY COMMAND
    # ==========================================
    @app_commands.command(name="copy", description="Copies and transmits an exact message anonymously (Admin Only).")
    @app_commands.describe(
        message="The exact text string to broadcast via the bot instance",
        target_channel="Target text channel to send to (Optional - defaults to current channel)"
    )
    async def copy(
        self, 
        interaction: discord.Interaction, 
        message: str, 
        target_channel: discord.TextChannel = None
    ):
        # 1. Admin restricted: Only user IDs in ADMIN_IDS can execute
        if interaction.user.id not in self.bot.ADMIN_IDS:
            await interaction.response.send_message("❌ Security alert: Authorization failure.", ephemeral=True)
            return

        # 2. Ephemeral response: Output is hidden from everyone else
        await interaction.response.defer(ephemeral=True)

        destination = target_channel or interaction.channel

        try:
            # 3. Cross-channel broadcast
            await destination.send(message)
            await interaction.followup.send(
                f"🤫 **Secret Output:** Transmission successfully deployed to {destination.mention}!", 
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ Security Block: Lacking permissions to transmit in {destination.mention}.", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Systems Error: Transmission failed: {str(e)}", ephemeral=True)

    # ==========================================
    # PUBLIC PLAYER UTILITIES
    # ==========================================
    @app_commands.command(name="afk", description="Registers your status as AFK (Away From Keyboard)")
    @app_commands.describe(reason="Brief note explaining your absence")
    async def afk(self, interaction: discord.Interaction, reason: str = "Away from keyboard"):
        embed = discord.Embed(
            title="🌙 AFK Status Activated",
            description=f"{interaction.user.mention} is now marked as AFK.",
            color=discord.Color.dark_grey()
        )
        embed.add_field(name="Reason Logged", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Displays digital footprint details of a target member")
    @app_commands.describe(target="The player to view details for (leave empty for yourself)")
    async def userinfo(self, interaction: discord.Interaction, target: discord.Member = None):
        user = target or interaction.user
        
        roles = [role.mention for role in user.roles if role.name != "@everyone"]
        roles_str = ", ".join(roles) if roles else "No specialized roles"

        embed = discord.Embed(title=f"👤 Player Identification Matrix: {user.name}", color=discord.Color.cyan())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
        embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Roles Assigned", value=roles_str, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Fetches high-resolution profile avatar of a target node")
    @app_commands.describe(target="The member whose avatar you want to inspect")
    async def avatar(self, interaction: discord.Interaction, target: discord.Member = None):
        user = target or interaction.user
        embed = discord.Embed(title=f"🖼️ Avatar Display: {user.name}", color=discord.Color.purple())
        embed.set_image(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="report", description="Submits a formal player report to administration")
    @app_commands.describe(target="The suspect user node", reason="Detailed explanation of the violation")
    async def report(self, interaction: discord.Interaction, target: discord.Member, reason: str):
        await interaction.response.send_message(
            f"✅ Report logged successfully against {target.mention}. Moderation team notified.", 
            ephemeral=True
        )

        log_channel_id = getattr(self.bot, 'LOG_CHANNEL_ID', None)
        if log_channel_id:
            channel = self.bot.get_channel(log_channel_id)
            if channel:
                embed = discord.Embed(title="🚨 User Report Filed", color=discord.Color.dark_red())
                embed.add_field(name="Reported User", value=target.mention, inline=True)
                embed.add_field(name="Filed By", value=interaction.user.mention, inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                await channel.send(embed=embed)

    # ==========================================
    # STANDARD MODERATION COMMANDS
    # ==========================================
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
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unmute", description="Removes communication suppression matrix from an element")
    @app_commands.describe(target="Target user node to lift restriction from", reason="Reason logging input")
    async def unmute(self, interaction: discord.Interaction, target: discord.Member, reason: str = "Suppression lifted."):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack administrative rights.", ephemeral=True)
            return

        try:
            await target.timeout(None, reason=reason)
            embed = discord.Embed(title="🔊 Communication Vector Restored", color=discord.Color.green())
            embed.add_field(name="Target User", value=target.mention, inline=True)
            embed.add_field(name="Status Matrix", value="Timeout Lifted", inline=True)
            embed.add_field(name="Reason Logged", value=reason, inline=False)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Systems Error: Unmute protocol failed: {str(e)}", ephemeral=True)

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
            
            await interaction.response.send_message(embed=embed)
        except discord.NotFound:
            await interaction.response.send_message("❌ Execution Error: Specified user ID could not be resolved.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Systems Error: Unban protocol failed: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
    

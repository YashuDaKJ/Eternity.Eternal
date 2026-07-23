import os
import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
from datetime import timedelta
import core_data as faction_data  # Linked with your data module for AI context

# ==========================================
# INTERACTIVE HELP UI LAYOUT MODULE
# ==========================================
class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Core Utilities", 
                description="AI interface and behavioral guidance", 
                emoji="🌌"
            ),
            discord.SelectOption(
                label="Moderation Vectors", 
                description="Administrative commands for faction order", 
                emoji="🛡️"
            )
        ]
        super().__init__(placeholder="Select system architecture...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Core Utilities":
            embed = discord.Embed(title="🌌 Core System Utilities", color=discord.Color.from_rgb(0, 191, 255))
            embed.add_field(name="`/ask`", value="Direct query interface to the core AI instance from any permitted node.", inline=False)
            embed.add_field(name="`/behave`", value="Issue a behavioral warning and protocol reminder to an element.", inline=False)
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "Moderation Vectors":
            embed = discord.Embed(title="🛡️ Moderation & Enforcement Vectors", color=discord.Color.red())
            embed.add_field(name="`/warn`", value="Issue a formal policy violation notice to an element.", inline=False)
            embed.add_field(name="`/timeout`", value="Apply temporary communication suppression matrix (Mute).", inline=False)
            embed.add_field(name="`/clear`", value="Purge a specific quantity of transmission frames from the channel.", inline=False)
            embed.add_field(name="`/kick`", value="Remove a target element from the active guild framework.", inline=False)
            embed.add_field(name="`/ban`", value="Permanently sever a disruptive element's network connection.", inline=False)
            embed.add_field(name="`/unban`", value="Restore connection capabilities to a previously terminated element.", inline=False)
            await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(HelpDropdown())


# ==========================================
# MAIN EXTENSION COMMAND MODULE FOR ETERNITY
# ==========================================
class EternityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _is_authorized(self, interaction: discord.Interaction) -> bool:
        """
        Internal authorization matrix. Validates if the user is a designated 
        High Administrator or possesses the required Moderator Role.
        """
        if interaction.user.id in self.bot.ADMIN_IDS:
            return True
        if any(role.id == self.bot.MODERATOR_ROLE_ID for role in interaction.user.roles):
            return True
        return False

    @app_commands.command(name="help", description="Access the functional operations directory of Eternity")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌌 Eternity Operations & Moderation System 🌌",
            description="Welcome, authorized operations asset. Select a module from the dropdown to view available directives.",
            color=discord.Color.from_rgb(0, 191, 255)
        )
        embed.set_footer(text="System Architecture Online")
        await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)

    # ==========================================
    # CORE UTILITIES (/ask & /behave)
    # ==========================================

    @app_commands.command(name="ask", description="Query Eternity anywhere on the communication network")
    @app_commands.describe(question="Input transaction string for the AI database")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        try:
            combined_instructions = (
                f"{self.bot.SYSTEM_PROMPT}\n\n"
                f"Core Faction Knowledge Base:\n{faction_data.FACTION_PROMPT}"
            )
            
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash', 
                system_instruction=combined_instructions
            )
            
            response = model.generate_content(question)
            answer = response.text
            formatted_response = f"**Input Query:** {question}\n\n✨ **Eternity Output:** {answer}"
            
            if len(formatted_response) > 2000:
                await interaction.followup.send(f"**Input Query:** {question}")
                chunks = [answer[i:i+1900] for i in range(0, len(answer), 1900)]
                for chunk in chunks:
                    await interaction.followup.send(f"**Eternity Segment:** {chunk}")
            else:
                await interaction.followup.send(formatted_response)
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                await interaction.followup.send("💠 *The cosmic frequencies are currently overloaded, my friends! Let the stars align and try again in a brief moment!*")
            else:
                await interaction.followup.send(f"💠 System Core Exception: {str(e)}")

    @app_commands.command(name="behave", description="Issues a formal protocol & behavior directive to an element")
    @app_commands.describe(target="The targeted user node", rule="The specific protocol or behavior standard to enforce")
    async def behave(self, interaction: discord.Interaction, target: discord.Member, rule: str = "Standard conduct & decorum protocol."):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack the administrative rights to execute this enforcement vector.", ephemeral=True)
            return

        embed = discord.Embed(
            title="⚠️ Behavior & Conduct Protocol Issued",
            description=f"Attention {target.mention}, you are instructed to immediately adjust your conduct to maintain network order.",
            color=discord.Color.gold()
        )
        embed.add_field(name="Directed To", value=target.mention, inline=True)
        embed.add_field(name="Issued By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Protocol Directive", value=rule, inline=False)
        embed.set_footer(text="Failure to comply will result in escalation to disciplinary vectors.")

        await interaction.response.send_message(content=target.mention, embed=embed)

    @ask.error
    async def command_cooldown_error_handler(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏰ *Hold your energy, guardian! This command matrix is cooling down. Try again in {error.retry_after:.1f}s.*", 
                ephemeral=True
            )
        else:
            try:
                await interaction.response.send_message(f"💠 Systems Error: {str(error)}", ephemeral=True)
            except:
                await interaction.followup.send(f"💠 Systems Error: {str(error)}")

    # ==========================================
    # CORE MODERATION ENFORCEMENT ENGINE
    # ==========================================

    @app_commands.command(name="warn", description="Issues a formal protocol infraction warning to a target member")
    @app_commands.describe(target="The user node receiving the warning infraction", reason="Reason for issuing the notice")
    async def warn(self, interaction: discord.Interaction, target: discord.Member, reason: str):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack the administrative rights to execute this enforcement vector.", ephemeral=True)
            return

        if target.top_role >= interaction.user.top_role and interaction.user.id not in self.bot.ADMIN_IDS:
            await interaction.response.send_message("❌ Command execution denied: Insufficient hierarchy permissions.", ephemeral=True)
            return

        embed = discord.Embed(title="⚠️ Protocol Infraction Notice", color=discord.Color.red())
        embed.add_field(name="Target Element", value=target.mention, inline=True)
        embed.add_field(name="Issued By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Infraction Reason", value=reason, inline=False)
        embed.set_footer(text="Further policy violations will result in automatic network containment protocols.")

        try:
            await target.send(f"⚠️ You have received an official warning in **{interaction.guild.name}**.\n**Reason:** {reason}")
        except discord.Forbidden:
            pass

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="timeout", description="Applies communication suppression matrix to an element (Mute)")
    @app_commands.describe(target="Target user node", minutes="Suppression duration in minutes", reason="Log input")
    async def timeout(self, interaction: discord.Interaction, target: discord.Member, minutes: int, reason: str = "Communication disruption."):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack the administrative rights to execute this enforcement vector.", ephemeral=True)
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

    @app_commands.command(name="clear", description="Purges a specific quantity of transmission frames from the active channel")
    @app_commands.describe(amount="Number of network message logs to systematically erase")
    async def clear(self, interaction: discord.Interaction, amount: int):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack the administrative rights to execute this enforcement vector.", ephemeral=True)
            return

        if amount <= 0 or amount > 100:
            await interaction.response.send_message("❌ Operational Error: Quantities must be between 1 and 100 entries.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ Operations Success: Successfully purged `{len(deleted)}` historical message entries.", ephemeral=True)

    @app_commands.command(name="kick", description="Ejects a target member from the active server footprint")
    @app_commands.describe(target="The specific user node to kick", reason="Reason logging input")
    async def kick(self, interaction: discord.Interaction, target: discord.Member, reason: str = "Standard administrative mitigation."):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack the administrative rights to execute this enforcement vector.", ephemeral=True)
            return

        if target.top_role >= interaction.user.top_role and interaction.user.id not in self.bot.ADMIN_IDS:
            await interaction.response.send_message("❌ Command execution denied: Insufficient hierarchy permissions.", ephemeral=True)
            return
        
        await target.kick(reason=reason)
        embed = discord.Embed(title="👢 Element Ejected", color=discord.Color.orange())
        embed.add_field(name="Target User", value=target.mention, inline=True)
        embed.add_field(name="Enforcement action", value="Ejection (Kick)", inline=True)
        embed.add_field(name="Reason Logged", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ban", description="Terminates a member's network connection permanently")
    @app_commands.describe(target="The specific user user to ban", reason="Reason logging input")
    async def ban(self, interaction: discord.Interaction, target: discord.Member, reason: str = "Violation of standard protocol."):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack the administrative rights to execute this enforcement vector.", ephemeral=True)
            return

        if target.top_role >= interaction.user.top_role and interaction.user.id not in self.bot.ADMIN_IDS:
            await interaction.response.send_message("❌ Command execution denied: Insufficient hierarchy permissions.", ephemeral=True)
            return
        
        await target.ban(reason=reason)
        embed = discord.Embed(title="🔨 Element Connection Terminated", color=discord.Color.red())
        embed.add_field(name="Target User", value=target.mention, inline=True)
        embed.add_field(name="Enforcement action", value="Permanent Ban", inline=True)
        embed.add_field(name="Reason Logged", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unban", description="Restores server connection rights to a previously banned ID")
    @app_commands.describe(user_id="The exact digital snowflake ID string of the target user", reason="Reason logging input")
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "Sanction period expired."):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security protocols alert: You lack the administrative rights to execute this enforcement vector.", ephemeral=True)
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
            await interaction.response.send_message("❌ Execution Error: The specified user ID matrix could not be resolved on the Discord API grid.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Systems Error: Unban protocol failed. Details: {str(e)}", ephemeral=True)

# ==========================================
# EXTENSION INITIALIZATION MATRIX
# ==========================================
async def setup(bot):
    await bot.add_cog(EternityCommands(bot))
                          

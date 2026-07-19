import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import requests
from datetime import timedelta
import core_data as faction_data  # Updated: Perfectly linked to the new secure config!

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
        
        # Check if the user has the required Moderator Role ID
        if any(role.id == self.bot.MODERATOR_ROLE_ID for role in interaction.user.roles):
            return True
            
        return False

    # Dropdown interactive logic for system diagnostics/help
    class HelpDropdown(discord.ui.Select):
        def __init__(self, special_channel_id):
            self.special_channel_id = special_channel_id
            options = [
                discord.SelectOption(label="Core Utilities", description="Basic interaction framework and AI interfaces", emoji="🌌"),
                discord.SelectOption(label="Moderation Vectors", description="Administrative commands for faction order", emoji="🛡️")
            ]
            super().__init__(placeholder="Select system architecture...", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            if self.values[0] == "Core Utilities":
                embed = discord.Embed(title="🌌 Core System Utilities", color=discord.Color.from_rgb(0, 191, 255))
                embed.add_field(name="`?ping`", value="Execute network speed diagnostics.", inline=False)
                embed.add_field(name="`/ask`", value="Direct query interface to the core AI instance from any permitted node.", inline=False)
                embed.add_field(name="`/analyze`", value="Provide binary assets (images/files) for standard analytical scan.", inline=False)
                embed.add_field(name="💬 AI Integration", value=f"Continuous response node active in <#{self.special_channel_id}>.", inline=False)
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
        def __init__(self, special_channel_id):
            super().__init__()
            self.add_item(EternityCommands.HelpDropdown(special_channel_id))

    @app_commands.command(name="help", description="Access the functional operations directory of Eternity")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌌 Eternity Command & Matrix Interface 🌌",
            description="Welcome, authorized operations asset. Select a directive module from the dropdown to proceed.",
            color=discord.Color.from_rgb(0, 191, 255)
        )
        embed.set_footer(text="System Architecture Online")
        await interaction.response.send_message(embed=embed, view=self.HelpView(self.bot.SPECIAL_CHANNEL_ID), ephemeral=True)

    @app_commands.command(name="ask", description="Query Eternity anywhere on the communication network")
    @app_commands.describe(question="Input transaction string for the AI database")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        try:
            # FIXED: Merged faction prompts so /ask is smart, and switched to gemini-2.5-flash-lite!
            combined_instructions = (
                f"{self.bot.SYSTEM_PROMPT}\n\n"
                f"Core Faction Knowledge Base:\n{faction_data.FACTION_PROMPT}"
            )
            
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash-lite', 
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
            # Added a smart error shield check here too just in case!
            if "429" in str(e) or "quota" in str(e).lower():
                await interaction.followup.send("💠 *The cosmic frequencies are currently overloaded, my friends! Let the stars align and try again in a brief moment!*")
            else:
                await interaction.followup.send(f"💠 System Core Exception: {str(e)}")

    @app_commands.command(name="analyze", description="Upload file assets for system vision processing")
    @app_commands.describe(prompt="Context description or processing instructions", attachment="Target media file array")
    async def analyze(self, interaction: discord.Interaction, prompt: str, attachment: discord.Attachment):
        await interaction.response.defer()
        if not attachment.content_type:
            await interaction.followup.send("💠 Data processing aborted: Missing signature array.")
            return
        try:
            file_response = requests.get(attachment.url)
            attachment_data = {
                'mime_type': attachment.content_type,
                'data': file_response.content
            }
            response_text = await self.bot.get_gemini_response(prompt, interaction.user.id, attachment_data)
            await interaction.followup.send(f"🌌 **Vision Array Diagnostics:** {response_text}")
        except Exception as e:
            await interaction.followup.send(f"💠 Analytics process error: {str(e)}")

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
        except ValueError:
            await interaction.response.send_message("❌ Formatting Error: ID must be numerical.", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ Target ID missing from global isolation arrays.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EternityCommands(bot))
        

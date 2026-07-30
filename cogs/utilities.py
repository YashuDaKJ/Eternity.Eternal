import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import core_data as faction_data

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
            embed.add_field(name="`/ask`", value="Direct query interface to the core AI instance.", inline=False)
            embed.add_field(name="`/behave`", value="Issue a behavioral warning and protocol reminder.", inline=False)
            embed.add_field(name="`/userinfo`", value="Check detailed stats of a user node.", inline=False)
            embed.add_field(name="`/avatar`", value="Fetch high resolution avatar.", inline=False)
            embed.add_field(name="`/afk`", value="Set your away status.", inline=False)
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "Moderation Vectors":
            embed = discord.Embed(title="🛡️ Moderation & Enforcement Vectors", color=discord.Color.red())
            embed.add_field(name="`/warn`", value="Issue a formal policy violation notice to an element.", inline=False)
            embed.add_field(name="`/timeout`", value="Apply temporary communication suppression matrix (Mute).", inline=False)
            embed.add_field(name="`/clear`", value="Purge a specific quantity of transmission frames.", inline=False)
            embed.add_field(name="`/kick`", value="Remove a target element from the active guild.", inline=False)
            embed.add_field(name="`/ban`", value="Permanently sever a disruptive element's connection.", inline=False)
            embed.add_field(name="`/unban`", value="Restore connection capabilities to a terminated element.", inline=False)
            await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(HelpDropdown())

# ==========================================
# UTILITIES COG MODULE
# ==========================================
class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _is_authorized(self, interaction: discord.Interaction) -> bool:
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

async def setup(bot):
    await bot.add_cog(Utilities(bot))
        

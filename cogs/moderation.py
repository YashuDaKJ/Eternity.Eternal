import discord
from discord import app_commands, ui
from discord.ext import commands
from datetime import timedelta, datetime

# ==========================================
# INTERACTIVE TOPIC BROWSER DROPDOWN
# ==========================================
class TopicSelectView(ui.View):
    def __init__(self, topics: list, collection, is_authorized_func, user):
        super().__init__(timeout=60)
        self.collection = collection
        self.is_authorized = is_authorized_func
        self.user = user

        # Construct options for the dropdown (Max 25 items allowed by Discord)
        options = [
            discord.SelectOption(
                label=str(topic).title(), 
                description=f"Browse entries logged under '{topic}'", 
                emoji="📂"
            ) for topic in topics[:25]
        ]

        self.select_menu = ui.Select(
            placeholder="🔍 Select a category to view entries...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        # Restrict interaction to the command executor
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ You are not authorized to interact with this menu.", ephemeral=True)
            return

        selected_topic = self.select_menu.values[0].lower()
        
        # NOTE: If you are using 'motor' (async mongodb), you need 'await collection.find(...).to_list(length=10)'
        # If you are using standard 'pymongo' (sync), keep it as 'list(collection.find(...).limit(10))'
        try:
            records = await self.collection.find({"topic": selected_topic}).to_list(length=10)
        except TypeError:
            # Fallback for sync PyMongo
            records = list(self.collection.find({"topic": selected_topic}).limit(10))

        if not records:
            await interaction.response.send_message(f"ℹ️ No active entries found for topic `{selected_topic}`.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📁 Database Records: {selected_topic.title()}",
            description=f"Showing latest entries logged under **{selected_topic}**",
            color=discord.Color.blue()
        )

        for idx, rec in enumerate(records, 1):
            target_str = f"<@{rec['user_id']}>" if "user_id" in rec else "N/A"
            mod_str = f"<@{rec['mod_id']}>" if "mod_id" in rec else "System"
            reason_str = rec.get("reason", "No detailed notes provided.")
            
            embed.add_field(
                name=f"Case #{rec.get('case_id', idx)}",
                value=f"**Target:** {target_str}\n**Logged By:** {mod_str}\n**Details:** {reason_str}",
                inline=False
            )

        embed.set_footer(text="To share a specific record publicly, use /search_logs")
        await interaction.response.send_message(embed=embed, ephemeral=True)


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
    # DATABASE MANAGEMENT COMMANDS
    # ==========================================
    @app_commands.command(name="add_log", description="Create a general or user-specific database log")
    @app_commands.describe(
        topic="The category name (e.g., Rules, GeneralNotes, Coords)",
        reason="The data, text, or information you want to store",
        target="Optional: Tag a user if this record belongs to someone"
    )
    async def add_log(
        self, 
        interaction: discord.Interaction, 
        topic: str, 
        reason: str, 
        target: discord.Member = None
    ):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security alert: You lack administrative rights.", ephemeral=True)
            return

        if not hasattr(self.bot, 'db') or self.bot.db is None:
            await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
            return

        collection = self.bot.db["moderation_logs"]
        case_id = int(discord.utils.utcnow().timestamp())

        log_data = {
            "case_id": case_id,
            "user_id": target.id if target else None,
            "mod_id": interaction.user.id,
            "topic": topic.strip().lower(),
            "reason": reason,
            "timestamp": datetime.utcnow()
        }

        # Async (Motor) aur Sync (PyMongo) dono ke liye insertion handling
        try:
            await collection.insert_one(log_data)
        except TypeError:
            collection.insert_one(log_data)

        embed = discord.Embed(title="✅ Database Record Saved", color=discord.Color.green())
        embed.add_field(name="Category/Topic", value=topic.title(), inline=True)
        embed.add_field(name="Target User", value=target.mention if target else "None (General Note)", inline=True)
        embed.add_field(name="Record ID", value=f"`#{case_id}`", inline=True)
        embed.add_field(name="Content/Data", value=reason, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    
    @app_commands.command(name="browse_categories", description="Browse all registered data categories/topics via a menu")
    async def browse_categories(self, interaction: discord.Interaction):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security alert: You lack administrative rights.", ephemeral=True)
            return

        if not hasattr(self.bot, 'db') or self.bot.db is None:
            await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
            return

        collection = self.bot.db["moderation_logs"]
        
        # Handle both Async (Motor) and Sync (PyMongo) queries
        try:
            topics = await collection.distinct("topic")
        except TypeError:
            topics = collection.distinct("topic")

        if not topics:
            await interaction.response.send_message("📂 No recorded categories found in the database.", ephemeral=True)
            return

        view = TopicSelectView(
            topics=topics, 
            collection=collection, 
            is_authorized_func=self._is_authorized, 
            user=interaction.user
        )

        embed = discord.Embed(
            title="📂 Database Category Browser",
            description=f"Found **{len(topics)}** registered categories.\nSelect an option below to view entries.",
            color=discord.Color.teal()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="search_logs", description="Search specific database records with optional user filtering")
    @app_commands.describe(
        topic="The exact category name to fetch (e.g., Spam)",
        target="Optional: Filter records by a specific user",
        is_public="True = Visible to everyone | False = Visible ONLY to you (Default)"
    )
    async def search_logs(self, interaction: discord.Interaction, topic: str, target: discord.Member = None, is_public: bool = False):
        if not self._is_authorized(interaction):
            await interaction.response.send_message("❌ Security alert: You lack administrative rights.", ephemeral=True)
            return

        if not hasattr(self.bot, 'db') or self.bot.db is None:
            await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
            return

        query = {"topic": topic.strip().lower()}
        if target:
            query["user_id"] = target.id

        collection = self.bot.db["moderation_logs"]
        
        # Handle both Async (Motor) and Sync (PyMongo) queries
        try:
            records = await collection.find(query).to_list(length=10)
        except TypeError:
            records = list(collection.find(query).limit(10))

        if not records:
            msg = f"❌ No records matching topic `{topic.title()}`"
            if target:
                msg += f" for user {target.mention}"
            await interaction.response.send_message(msg, ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📋 Search Results: {topic.title()}",
            description=f"Filter Target: {target.mention if target else 'All Users'}",
            color=discord.Color.gold()
        )

        for idx, rec in enumerate(records, 1):
            target_str = f"<@{rec['user_id']}>" if "user_id" in rec else "N/A"
            mod_str = f"<@{rec['mod_id']}>" if "mod_id" in rec else "System"
            reason_str = rec.get("reason", "No detailed notes provided.")

            embed.add_field(
                name=f"Case #{rec.get('case_id', idx)}",
                value=f"**Target:** {target_str}\n**Logged By:** {mod_str}\n**Details:** {reason_str}",
                inline=False
            )

        embed.set_footer(text=f"Requested by {interaction.user.name} • Public Mode: {is_public}")
        await interaction.response.send_message(embed=embed, ephemeral=not is_public)

    # ==========================================
    # ADMIN EXCLUSIVE COVERT COPY COMMAND
    # ==========================================
    @app_commands.command(name="copy", description="Copies raw text or replies/clones an existing message anonymously.")
    @app_commands.describe(
        message_input="Enter raw text to broadcast OR a Message ID to target",
        reply_text="Optional text to reply directly to the target Message ID",
        target_channel="Target text channel to send to (Optional - defaults to current channel)"
    )
    async def copy(self, interaction: discord.Interaction, message_input: str, reply_text: str = None, target_channel: discord.TextChannel = None):
        if interaction.user.id not in self.bot.ADMIN_IDS:
            await interaction.response.send_message("❌ Security alert: Authorization failure.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        destination = target_channel or interaction.channel

        try:
            if message_input.strip().isdigit():
                msg_id = int(message_input.strip())
                original_msg = await interaction.channel.fetch_message(msg_id)

                if reply_text:
                    await original_msg.reply(reply_text)
                    await interaction.followup.send(f"🤫 **Secret Output:** Replied to message `{msg_id}` in {interaction.channel.mention}!", ephemeral=True)
                else:
                    files = [await attachment.to_file() for attachment in original_msg.attachments]
                    new_msg = await destination.send(content=original_msg.content, files=files)
                    for reaction in original_msg.reactions:
                        try:
                            await new_msg.add_reaction(reaction.emoji)
                        except discord.HTTPException:
                            pass
                    await interaction.followup.send(f"🤫 **Secret Output:** Cloned message `{msg_id}` to {destination.mention}!", ephemeral=True)
            else:
                await destination.send(content=message_input)
                await interaction.followup.send(f"🤫 **Secret Output:** Transmission successfully deployed to {destination.mention}!", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send(f"❌ Systems Error: Message ID `{message_input}` not found in this channel.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"❌ Security Block: Lacking permissions in {destination.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Systems Error: Action failed: {str(e)}", ephemeral=True)

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
        await interaction.response.send_message(f"✅ Report logged successfully against {target.mention}. Moderation team notified.", ephemeral=True)
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
        

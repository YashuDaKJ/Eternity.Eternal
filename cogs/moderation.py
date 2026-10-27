import time
from datetime import timedelta, datetime, timezone

import discord
from discord import app_commands, ui
from discord.ext import commands
from pymongo import ReturnDocument

MAX_TIMEOUT_MIN = 40320  # Discord's 28 day limit


def _trim(text: str, n: int) -> str:
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def gq(guild_id: int, **extra) -> dict:
    """Guild-scoped query. Old records without guild_id still match."""
    q = {"$or": [{"guild_id": guild_id}, {"guild_id": {"$exists": False}}]}
    q.update(extra)
    return q


def _fmt_record(rec: dict) -> str:
    target = f"<@{rec['user_id']}>" if rec.get("user_id") else "N/A"
    mod = f"<@{rec['mod_id']}>" if rec.get("mod_id") else "System"
    return (f"**Target:** {target}\n**Logged By:** {mod}\n"
            f"**Details:** {_trim(rec.get('reason') or 'No notes.', 300)}")


# ==========================================
# TOPIC BROWSER DROPDOWN
# ==========================================
class TopicSelectView(ui.View):
    def __init__(self, topics: list, collection, guild_id: int, user):
        super().__init__(timeout=60)
        self.collection = collection
        self.guild_id = guild_id
        self.user = user

        options = [
            discord.SelectOption(
                label=_trim(str(t).title(), 100),
                value=str(t)[:100],
                description=_trim(f"Entries logged under '{t}'", 100),
                emoji="📂",
            )
            for t in topics[:25]
        ]
        self.select_menu = ui.Select(
            placeholder="🔍 Select a category to view entries...",
            min_values=1, max_values=1, options=options,
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ This menu isn't yours.", ephemeral=True)

        topic = self.select_menu.values[0]
        records = await (self.collection.find(gq(self.guild_id, topic=topic))
                         .sort("case_id", -1).to_list(length=10))
        if not records:
            return await interaction.response.send_message(f"ℹ️ No entries for `{topic}`.", ephemeral=True)

        embed = discord.Embed(
            title=f"📁 Database Records: {topic.title()}",
            description=f"Latest entries under **{topic}**",
            color=discord.Color.blue(),
        )
        for rec in records:
            embed.add_field(name=f"Case #{rec.get('case_id', '?')}", value=_fmt_record(rec), inline=False)
        embed.set_footer(text="To share a record publicly, use /search_logs")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# MODERATION COG
# ==========================================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channels: dict[int, int] = {}
        self.afk: dict[tuple[int, int], dict] = {}

    async def cog_load(self):
        if self.bot.db is None:
            return
        try:
            docs = await self.bot.db["afk"].find({}).to_list(length=5000)
            for d in docs:
                self.afk[(d["guild_id"], d["user_id"])] = {"reason": d.get("reason", ""), "since": d.get("since", 0)}
        except Exception as e:
            print(f"⚠️ Could not load AFK list: {e}", flush=True)

    # ---------- helpers ----------
    def _is_authorized(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False
        if interaction.user.id in self.bot.ADMIN_IDS:
            return True
        mod_role = getattr(self.bot, "MODERATOR_ROLE_ID", None)
        return any(r.id == mod_role for r in getattr(interaction.user, "roles", []))

    async def _deny(self, interaction: discord.Interaction):
        await interaction.response.send_message("❌ Security alert: You lack administrative rights.", ephemeral=True)

    def _check_target(self, interaction, target: discord.Member, bot_must_outrank=True):
        guild = interaction.guild
        if target.id == interaction.user.id:
            return "You can't target yourself."
        if target.id == self.bot.user.id:
            return "Nice try."
        if target.id == guild.owner_id:
            return "You can't act on the server owner."
        is_admin = interaction.user.id in self.bot.ADMIN_IDS
        if not is_admin and target.top_role >= interaction.user.top_role:
            return "Insufficient hierarchy: that member's top role is equal to or above yours."
        if bot_must_outrank and target.top_role >= guild.me.top_role:
            return "My role isn't high enough. Move my role above that member's top role."
        return None

    async def _fail(self, interaction: discord.Interaction, e: Exception):
        if isinstance(e, discord.Forbidden):
            msg = "❌ I lack permission to do that (check my role position and permissions)."
        else:
            msg = f"❌ Action failed: {_trim(e, 200)}"
        await interaction.followup.send(msg, ephemeral=True)

    async def _get_log_channel(self, guild: discord.Guild):
        cid = self.log_channels.get(guild.id)
        if cid is None:
            cid = 0
            if self.bot.db is not None:
                doc = await self.bot.db["guild_settings"].find_one({"_id": str(guild.id)})
                cid = (doc or {}).get("log_channel", 0)
            self.log_channels[guild.id] = cid
        if not cid:
            return None
        ch = guild.get_channel(cid)
        return ch if isinstance(ch, discord.abc.Messageable) else None

    async def _save_case(self, guild_id, topic, mod_id, reason, user_id=None):
        db = self.bot.db
        if db is None:
            return None
        try:
            counter = await db["counters"].find_one_and_update(
                {"_id": f"cases:{guild_id}"}, {"$inc": {"seq": 1}},
                upsert=True, return_document=ReturnDocument.AFTER,
            )
            case_id = counter["seq"]
            await db["moderation_logs"].insert_one({
                "case_id": case_id, "guild_id": guild_id, "user_id": user_id, "mod_id": mod_id,
                "topic": topic.strip().lower(), "reason": reason,
                "timestamp": datetime.now(timezone.utc),
            })
            return case_id
        except Exception as e:
            print(f"⚠️ Case save failed: {e}", flush=True)
            return None

    async def _record(self, guild, action, mod, reason, target=None, color=discord.Color.orange()):
        case_id = await self._save_case(guild.id, action, mod.id, reason, target.id if target else None)
        channel = await self._get_log_channel(guild)
        if channel:
            embed = discord.Embed(
                title=f"📋 Case #{case_id if case_id else 'N/A'} · {action.title()}",
                color=color, timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="Target", value=target.mention if target else "N/A", inline=True)
            embed.add_field(name="Moderator", value=mod.mention, inline=True)
            embed.add_field(name="Reason", value=_trim(reason, 1000), inline=False)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass
        return case_id

    async def _dm(self, user, guild, action: str, reason: str):
        try:
            await user.send(f"You received a **{action}** in **{guild.name}**.\nReason: {reason}")
        except (discord.Forbidden, discord.HTTPException):
            pass

    # ---------- log channel ----------
    @app_commands.command(name="setlogchannel", description="Set the channel for moderation logs and reports (Admin)")
    @app_commands.guild_only()
    @app_commands.describe(channel="Channel where cases and reports will be posted")
    async def setlogchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        is_admin = interaction.user.id in self.bot.ADMIN_IDS or interaction.user.guild_permissions.administrator
        if not is_admin:
            return await self._deny(interaction)
        perms = channel.permissions_for(interaction.guild.me)
        if not (perms.view_channel and perms.send_messages and perms.embed_links):
            return await interaction.response.send_message(
                "❌ I need View, Send Messages and Embed Links in that channel.", ephemeral=True)
        if self.bot.db is None:
            return await interaction.response.send_message("❌ Database unavailable.", ephemeral=True)
        await self.bot.db["guild_settings"].update_one(
            {"_id": str(interaction.guild.id)}, {"$set": {"log_channel": channel.id}}, upsert=True)
        self.log_channels[interaction.guild.id] = channel.id
        await interaction.response.send_message(f"✅ Moderation log set to {channel.mention}.", ephemeral=True)

    # ---------- database commands ----------
    @app_commands.command(name="add_log", description="Create a general or user-specific database log")
    @app_commands.guild_only()
    @app_commands.describe(topic="Category (e.g., Rules, GeneralNotes)", reason="The text to store",
                           target="Optional: user this record belongs to")
    async def add_log(self, interaction: discord.Interaction, topic: str, reason: str, target: discord.Member = None):
        if not self._is_authorized(interaction):
            return await self._deny(interaction)
        if self.bot.db is None:
            return await interaction.response.send_message("❌ Database unavailable.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        case_id = await self._save_case(interaction.guild.id, topic, interaction.user.id, reason,
                                        target.id if target else None)
        if case_id is None:
            return await interaction.followup.send("❌ Could not save the record.", ephemeral=True)
        embed = discord.Embed(title="✅ Database Record Saved", color=discord.Color.green())
        embed.add_field(name="Category", value=topic.title(), inline=True)
        embed.add_field(name="Target", value=target.mention if target else "None (General Note)", inline=True)
        embed.add_field(name="Record ID", value=f"`#{case_id}`", inline=True)
        embed.add_field(name="Content", value=_trim(reason, 1000), inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="browse_categories", description="Browse all registered data categories via a menu")
    @app_commands.guild_only()
    async def browse_categories(self, interaction: discord.Interaction):
        if not self._is_authorized(interaction):
            return await self._deny(interaction)
        if self.bot.db is None:
            return await interaction.response.send_message("❌ Database unavailable.", ephemeral=True)
        collection = self.bot.db["moderation_logs"]
        topics = await collection.distinct("topic", gq(interaction.guild.id))
        if not topics:
            return await interaction.response.send_message("📂 No categories recorded yet.", ephemeral=True)
        view = TopicSelectView(topics, collection, interaction.guild.id, interaction.user)
        embed = discord.Embed(
            title="📂 Database Category Browser",
            description=f"Found **{len(topics)}** categories (showing up to 25).\nSelect one below.",
            color=discord.Color.teal())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="search_logs", description="Search database records with optional user filtering")
    @app_commands.guild_only()
    @app_commands.describe(topic="Exact category (e.g., warn, ban, spam)", target="Optional: filter by user",
                           is_public="True = visible to everyone | False = only you (default)")
    async def search_logs(self, interaction: discord.Interaction, topic: str,
                          target: discord.Member = None, is_public: bool = False):
        if not self._is_authorized(interaction):
            return await self._deny(interaction)
        if self.bot.db is None:
            return await interaction.response.send_message("❌ Database unavailable.", ephemeral=True)
        extra = {"topic": topic.strip().lower()}
        if target:
            extra["user_id"] = target.id
        records = await (self.bot.db["moderation_logs"].find(gq(interaction.guild.id, **extra))
                         .sort("case_id", -1).to_list(length=10))
        if not records:
            msg = f"❌ No records for topic `{topic.title()}`" + (f" and user {target.mention}" if target else "")
            return await interaction.response.send_message(msg, ephemeral=True)
        embed = discord.Embed(title=f"📋 Search Results: {topic.title()}",
                              description=f"Filter: {target.mention if target else 'All Users'}",
                              color=discord.Color.gold())
        for rec in records:
            embed.add_field(name=f"Case #{rec.get('case_id', '?')}", value=_fmt_record(rec), inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        await interaction.response.send_message(embed=embed, ephemeral=not is_public)

    @app_commands.command(name="warnings", description="View a member's warning history")
    @app_commands.guild_only()
    @app_commands.describe(target="The member to look up")
    async def warnings(self, interaction: discord.Interaction, target: discord.Member):
        if not self._is_authorized(interaction):
            return await self._deny(interaction)
        if self.bot.db is None:
            return await interaction.response.send_message("❌ Database unavailable.", ephemeral=True)
        col = self.bot.db["moderation_logs"]
        q = gq(interaction.guild.id, user_id=target.id, topic="warn")
        total = await col.count_documents(q)
        records = await col.find(q).sort("case_id", -1).to_list(length=10)
        embed = discord.Embed(title=f"⚠️ Warnings: {target.display_name}",
                              description=f"Total warnings: **{total}**", color=discord.Color.red())
        for rec in records:
            embed.add_field(name=f"Case #{rec.get('case_id', '?')}", value=_fmt_record(rec), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---------- covert copy ----------
    @app_commands.command(name="copy", description="Copies raw text or replies/clones an existing message anonymously.")
    @app_commands.guild_only()
    @app_commands.describe(message_input="Raw text to broadcast OR a Message ID",
                           reply_text="Optional text to reply to the Message ID",
                           target_channel="Target channel (defaults to current)")
    async def copy(self, interaction: discord.Interaction, message_input: str,
                   reply_text: str = None, target_channel: discord.TextChannel = None):
        if interaction.user.id not in self.bot.ADMIN_IDS:
            return await interaction.response.send_message("❌ Security alert: Authorization failure.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        destination = target_channel or interaction.channel
        try:
            if message_input.strip().isdigit():
                msg_id = int(message_input.strip())
                original = await interaction.channel.fetch_message(msg_id)
                if reply_text:
                    await original.reply(reply_text)
                    await interaction.followup.send(f"🤫 Replied to `{msg_id}`.", ephemeral=True)
                else:
                    files = [await a.to_file() for a in original.attachments]
                    new_msg = await destination.send(content=original.content, files=files)
                    for reaction in original.reactions:
                        try:
                            await new_msg.add_reaction(reaction.emoji)
                        except discord.HTTPException:
                            pass
                    await interaction.followup.send(f"🤫 Cloned `{msg_id}` to {destination.mention}.", ephemeral=True)
            else:
                await destination.send(content=message_input)
                await interaction.followup.send(f"🤫 Sent to {destination.mention}.", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send(f"❌ Message `{message_input}` not found in this channel.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"❌ No permission in {destination.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: {_trim(e, 200)}", ephemeral=True)

    # ---------- public utilities ----------
    @app_commands.command(name="afk", description="Mark yourself as AFK (Away From Keyboard)")
    @app_commands.guild_only()
    @app_commands.describe(reason="Why you're away")
    async def afk_cmd(self, interaction: discord.Interaction, reason: str = "Away from keyboard"):
        reason = _trim(discord.utils.escape_mentions(reason), 100)
        key = (interaction.guild.id, interaction.user.id)
        since = int(time.time())
        self.afk[key] = {"reason": reason, "since": since}
        if self.bot.db is not None:
            await self.bot.db["afk"].update_one(
                {"_id": f"{key[0]}:{key[1]}"},
                {"$set": {"guild_id": key[0], "user_id": key[1], "reason": reason, "since": since}}, upsert=True)
        embed = discord.Embed(title="🌙 AFK Status Activated",
                              description=f"{interaction.user.mention} is now AFK.", color=discord.Color.dark_grey())
        embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None or not self.afk:
            return
        gid = message.guild.id
        key = (gid, message.author.id)
        if key in self.afk:
            self.afk.pop(key, None)
            if self.bot.db is not None:
                try:
                    await self.bot.db["afk"].delete_one({"_id": f"{gid}:{message.author.id}"})
                except Exception:
                    pass
            try:
                await message.channel.send(f"👋 Welcome back {message.author.mention}, AFK removed.", delete_after=8)
            except discord.HTTPException:
                pass

        notes, seen = [], set()
        for m in message.mentions:
            if m.bot or m.id == message.author.id or m.id in seen:
                continue
            seen.add(m.id)
            info = self.afk.get((gid, m.id))
            if info:
                notes.append(f"💤 **{m.display_name}** is AFK: {info['reason']} (<t:{info['since']}:R>)")
        if notes:
            try:
                await message.reply("\n".join(notes[:5]), mention_author=False,
                                    allowed_mentions=discord.AllowedMentions.none(), delete_after=15)
            except discord.HTTPException:
                pass

    @app_commands.command(name="userinfo", description="Displays details of a member")
    @app_commands.guild_only()
    @app_commands.describe(target="Member to view (empty = yourself)")
    async def userinfo(self, interaction: discord.Interaction, target: discord.Member = None):
        user = target or interaction.user
        roles = [r.mention for r in user.roles if r.name != "@everyone"]
        embed = discord.Embed(title=f"👤 {user.name}", color=discord.Color.cyan())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
        embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "Unknown", inline=True)
        embed.add_field(name="Roles", value=_trim(", ".join(roles) if roles else "No roles", 1000), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Fetches a member's avatar")
    @app_commands.guild_only()
    @app_commands.describe(target="Member whose avatar you want")
    async def avatar(self, interaction: discord.Interaction, target: discord.Member = None):
        user = target or interaction.user
        embed = discord.Embed(title=f"🖼️ Avatar: {user.name}", color=discord.Color.purple())
        embed.set_image(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="report", description="Submit a report to the moderation team")
    @app_commands.guild_only()
    @app_commands.describe(target="The user you're reporting", reason="What happened")
    async def report(self, interaction: discord.Interaction, target: discord.Member, reason: str):
        await interaction.response.defer(ephemeral=True)
        case_id = await self._save_case(interaction.guild.id, "report", interaction.user.id, reason, target.id)
        channel = await self._get_log_channel(interaction.guild)
        delivered = False
        if channel:
            embed = discord.Embed(title="🚨 User Report Filed", color=discord.Color.dark_red(),
                                  timestamp=datetime.now(timezone.utc))
            embed.add_field(name="Reported User", value=target.mention, inline=True)
            embed.add_field(name="Filed By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=_trim(reason, 1000), inline=False)
            if case_id:
                embed.set_footer(text=f"Case #{case_id}")
            mod_role = getattr(self.bot, "MODERATOR_ROLE_ID", None)
            try:
                await channel.send(content=f"<@&{mod_role}>" if mod_role else None, embed=embed,
                                   allowed_mentions=discord.AllowedMentions(roles=True))
                delivered = True
            except discord.HTTPException:
                pass
        if delivered:
            msg = f"✅ Report filed against {target.mention}. The moderation team was notified."
        elif case_id:
            msg = f"⚠️ Report saved (case #{case_id}), but no log channel is set, so mods weren't pinged live."
        else:
            msg = "❌ I couldn't save your report. Please contact a moderator directly."
        await interaction.followup.send(msg, ephemeral=True)

    # ---------- enforcement ----------
    @app_commands.command(name="warn", description="Issue a formal warning to a member")
    @app_commands.guild_only()
    @app_commands.describe(target="Member to warn", reason="Reason")
    async def warn(self, interaction: discord.Interaction, target: discord.Member, reason: str):
        if not self._is_authorized(interaction):
            return await self._deny(interaction)
        err = self._check_target(interaction, target, bot_must_outrank=False)
        if err:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        await interaction.response.defer()
        case_id = await self._record(interaction.guild, "warn", interaction.user, reason, target, discord.Color.red())
        await self._dm(target, interaction.guild, "warning", reason)
        total = None
        if self.bot.db is not None:
            total = await self.bot.db["moderation_logs"].count_documents(
                gq(interaction.guild.id, user_id=target.id, topic="warn"))
        embed = discord.Embed(title="⚠️ Warning Issued", color=discord.Color.red())
        embed.add_field(name="Target", value=target.mention, inline=True)
        embed.add_field(name="Issued By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Case", value=f"#{case_id}" if case_id else "N/A", inline=True)
        if total is not None:
            embed.add_field(name="Total Warnings", value=str(total), inline=True)
        embed.add_field(name="Reason", value=_trim(reason, 1000), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="timeout", description="Mute a member for a set time")
    @app_commands.guild_only()
    @app_commands.describe(target="Member to mute", minutes="Duration in minutes (max 40320 = 28 days)", reason="Reason")
    async def timeout(self, interaction: discord.Interaction, target: discord.Member,
                      minutes: app_commands.Range[int, 1, MAX_TIMEOUT_MIN],
                      reason: str = "Communication disruption."):
        if not self._is_authorized(interaction):
            return await self._deny(interaction)
        err = self._check_target(interaction, target)
        if err:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        await interaction.response.defer()
        try:
            await target.timeout(timedelta(minutes=minutes), reason=_trim(reason, 500))
        except (discord.Forbidden, discord.HTTPException) as e:
            return await self._fail(interaction, e)
        case_id = await self._record(interaction.guild, "timeout", interaction.user,
                                     f"{reason} ({minutes} min)", target, discord.Color.gold())
        await self._dm(target, interaction.guild, f"timeout ({minutes} min)", reason)
        embed = discord.Embed(title="🔇 Member Timed Out", color=discord.Color.gold())
        embed.add_field(name="Target", value=target.mention, inline=True)
        embed.add_field(name="Duration", value=f"{minutes} min", inline=True)
        embed.add_field(name="Case", value=f"#{case_id}" if case_id else "N/A", inline=True)
        embed.add_field(name="Reason", value=_trim(reason, 1000), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="unmute", description="Remove a member's timeout")
    @app_commands.guild_only()
    @app_commands.describe(target="Member to unmute", reason="Reason")
    async def unmute(self, interaction: discord.Interaction, target: discord.Member, reason: str = "Timeout lifted."):
        if not self._is_authorized(interaction):
            return await self._deny(interaction)
        if target.id != interaction.user.id and target.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ My role isn't high enough for that member.", ephemeral=True)
        await interaction.response.defer()
        try:
            await target.timeout(None, reason=_trim(reason, 500))
        except (discord.Forbidden, discord.HTTPException) as e:
            return await self._fail(interaction, e)
        case_id = await self._record(interaction.guild, "unmute", interaction.user, reason, target, discord.Color.green())
        embed = discord.Embed(title="🔊 Timeout Lifted", color=discord.Color.green())
        embed.add_field(name="Target", value=target.mention, inline=True)
        embed.add_field(name="Case", value=f"#{case_id}" if case_id else "N/A", inline=True)
        embed.add_field(name="Reason", value=_trim(reason, 1000), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="clear", description="Delete a number of recent messages from this channel")
    @app_commands.guild_only()
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        if not self._is_authorized(interaction):
            return await self._deny(interaction)
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
        except (discord.Forbidden, discord.HTTPException, AttributeError) as e:
            return await self._fail(interaction, e)
        await self._record(interaction.guild, "clear", interaction.user,
                           f"Purged {len(deleted)} messages in #{interaction.channel.name}", None, discord.Color.light_grey())
        await interaction.followup.send(f"✅ Purged `{len(deleted)}` messages.", ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.guild_only()
    @app_commands.describe(target="Member to kick", reason="Reason")
    async def kick(self, interaction: discord.Interaction, target: discord.Member,
                   reason: str = "Standard administrative mitigation."):
        if not self._is_authorized(interaction):
            return await self._deny(interaction)
        err = self._check_target(interaction, target)
        if err:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        await interaction.response.defer()
        await self._dm(target, interaction.guild, "kick", reason)
        try:
            await target.kick(reason=_trim(reason, 500))
        except (discord.Forbidden, discord.HTTPException) as e:
            return await self._fail(interaction, e)
        case_id = await self._record(interaction.guild, "kick", interaction.user, reason, target, discord.Color.orange())
        embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange())
        embed.add_field(name="Target", value=f"{target} (`{target.id}`)", inline=True)
        embed.add_field(name="Case", value=f"#{case_id}" if case_id else "N/A", inline=True)
        embed.add_field(name="Reason", value=_trim(reason, 1000), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ban", description="Permanently ban a member")
    @app_commands.guild_only()
    @app_commands.describe(target="Member to ban", reason="Reason")
    async def ban(self, interaction: discord.Interaction, target: discord.Member,
                  reason: str = "Violation of server rules."):
        if not self._is_authorized(interaction):
            return await self._deny(interaction)
        err = self._check_target(interaction, target)
        if err:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        await interaction.response.defer()
        await self._dm(target, interaction.guild, "ban", reason)
        try:
            await target.ban(reason=_trim(reason, 500))
        except (discord.Forbidden, discord.HTTPException) as e:
            return await self._fail(interaction, e)
        case_id = await self._record(interaction.guild, "ban", interaction.user, reason, target, discord.Color.red())
        embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
        embed.add_field(name="Target", value=f"{target} (`{target.id}`)", inline=True)
        embed.add_field(name="Case", value=f"#{case_id}" if case_id else "N/A", inline=True)
        embed.add_field(name="Reason", value=_trim(reason, 1000), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.guild_only()
    @app_commands.describe(user_id="The user's Discord ID", reason="Reason")
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "Sanction period expired."):
        if not self._is_authorized(interaction):
            return await self._deny(interaction)
        try:
            uid = int(user_id.strip())
        except ValueError:
            return await interaction.response.send_message("❌ That isn't a valid user ID.", ephemeral=True)
        await interaction.response.defer()
        try:
            await interaction.guild.unban(discord.Object(id=uid), reason=_trim(reason, 500))
        except discord.NotFound:
            return await interaction.followup.send("❌ That user isn't banned.", ephemeral=True)
        except (discord.Forbidden, discord.HTTPException) as e:
            return await self._fail(interaction, e)
        case_id = await self._save_case(interaction.guild.id, "unban", interaction.user.id, reason, uid)
        channel = await self._get_log_channel(interaction.guild)
        if channel:
            try:
                await channel.send(f"🔓 **Unban** · case #{case_id or 'N/A'} · <@{uid}> by {interaction.user.mention}\nReason: {_trim(reason, 500)}",
                                   allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException:
                pass
        embed = discord.Embed(title="🔓 User Unbanned", color=discord.Color.green())
        embed.add_field(name="User ID", value=f"`{uid}`", inline=True)
        embed.add_field(name="Case", value=f"#{case_id}" if case_id else "N/A", inline=True)
        embed.add_field(name="Reason", value=_trim(reason, 1000), inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))

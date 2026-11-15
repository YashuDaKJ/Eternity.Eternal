from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

FEATURES = ("anti_raid", "audit_logs", "role_reactions", "tickets")


class CommunityAdmin(commands.Cog):
    """Opt-in, guild-scoped community tools with bounded in-memory state."""

    def __init__(self, bot):
        self.bot = bot
        self.recent_joins = defaultdict(deque)

    def _is_admin(self, interaction: discord.Interaction) -> bool:
        return bool(interaction.guild and (
            interaction.user.id in getattr(self.bot, "ADMIN_IDS", [])
            or interaction.user.guild_permissions.administrator
        ))

    async def _enabled(self, guild_id: int, feature: str) -> bool:
        if self.bot.db is None:
            return False
        doc = await self.bot.db["guild_settings"].find_one({"_id": str(guild_id)})
        return bool((doc or {}).get("features", {}).get(feature, False))

    async def _log(self, guild: discord.Guild, event: str, details: dict, actor_id=None):
        if self.bot.db is None:
            return
        record = {
            "guild_id": guild.id,
            "event": event,
            "actor_id": actor_id,
            "details": details,
            "timestamp": datetime.now(timezone.utc),
        }
        await self.bot.db["audit_events"].insert_one(record)
        settings = await self.bot.db["guild_settings"].find_one({"_id": str(guild.id)})
        channel = guild.get_channel((settings or {}).get("log_channel", 0))
        if channel and await self._enabled(guild.id, "audit_logs"):
            try:
                summary = discord.Embed(title=f"Audit: {event}", color=discord.Color.blurple(),
                                        timestamp=record["timestamp"])
                summary.description = "\n".join(f"**{k}:** {str(v)[:700]}" for k, v in details.items())[:4000]
                if actor_id:
                    summary.add_field(name="Actor", value=f"<@{actor_id}> (`{actor_id}`)", inline=False)
                await channel.send(embed=summary)
            except discord.HTTPException:
                pass

    async def _feature_guard(self, interaction, feature):
        if not await self._enabled(interaction.guild_id, feature):
            await interaction.response.send_message(
                f"This feature is off. An administrator can enable it with `/feature_toggle`.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="feature_toggle", description="Turn an optional community feature on or off")
    @app_commands.guild_only()
    @app_commands.describe(feature="Feature to configure", enabled="Whether the feature should be enabled")
    @app_commands.choices(feature=[app_commands.Choice(name=x.replace("_", " ").title(), value=x) for x in FEATURES])
    async def feature_toggle(self, interaction: discord.Interaction, feature: app_commands.Choice[str], enabled: bool):
        if not self._is_admin(interaction):
            return await interaction.response.send_message("Administrator permission required.", ephemeral=True)
        if self.bot.db is None:
            return await interaction.response.send_message("MongoDB is required to persist feature settings.", ephemeral=True)
        await self.bot.db["guild_settings"].update_one(
            {"_id": str(interaction.guild_id)},
            {"$set": {f"features.{feature.value}": enabled}}, upsert=True)
        await interaction.response.send_message(
            f"✅ **{feature.name}** is now {'on' if enabled else 'off'}.", ephemeral=True)

    @app_commands.command(name="feature_status", description="Show which optional community features are enabled")
    @app_commands.guild_only()
    async def feature_status(self, interaction: discord.Interaction):
        states = [f"**{name.replace('_', ' ').title()}:** {'on' if await self._enabled(interaction.guild_id, name) else 'off'}"
                  for name in FEATURES]
        await interaction.response.send_message("\n".join(states), ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        now = datetime.now(timezone.utc)
        joins = self.recent_joins[guild.id]
        joins.append(now)
        while joins and (now - joins[0]).total_seconds() > 60:
            joins.popleft()
        # Bounded by the 60-second window; no automatic bans/kicks are performed.
        if await self._enabled(guild.id, "anti_raid") and len(joins) >= 5:
            await self._log(guild, "anti_raid_join_burst", {"joins_in_60_seconds": len(joins), "window_seconds": 60})
        if await self._enabled(guild.id, "audit_logs"):
            await self._log(guild, "member_join", {"member_id": member.id, "account_created": member.created_at.isoformat()})

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if await self._enabled(member.guild.id, "audit_logs"):
            await self._log(member.guild, "member_leave", {"member_id": member.id})

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not await self._enabled(after.guild.id, "audit_logs"):
            return
        before_ids = {r.id for r in before.roles}
        after_ids = {r.id for r in after.roles}
        if before_ids != after_ids:
            await self._log(after.guild, "member_roles_changed", {
                "member_id": after.id,
                "added_role_ids": sorted(after_ids - before_ids),
                "removed_role_ids": sorted(before_ids - after_ids),
            })

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if await self._enabled(channel.guild.id, "audit_logs"):
            await self._log(channel.guild, "channel_created", {"channel_id": channel.id, "name": channel.name})

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if await self._enabled(channel.guild.id, "audit_logs"):
            await self._log(channel.guild, "channel_deleted", {"channel_id": channel.id, "name": channel.name})

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        if await self._enabled(role.guild.id, "audit_logs"):
            await self._log(role.guild, "role_created", {"role_id": role.id, "name": role.name})

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        if await self._enabled(role.guild.id, "audit_logs"):
            await self._log(role.guild, "role_deleted", {"role_id": role.id, "name": role.name})

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild and not message.author.bot and await self._enabled(message.guild.id, "audit_logs"):
            # Intentionally store metadata only, not deleted message content.
            await self._log(message.guild, "message_deleted", {"message_id": message.id,
                            "channel_id": message.channel.id, "author_id": message.author.id})

    @app_commands.command(name="role_reaction_add", description="Attach an emoji role to an existing message")
    @app_commands.guild_only()
    async def role_reaction_add(self, interaction: discord.Interaction, message_id: str,
                                emoji: str, role: discord.Role):
        if not self._is_admin(interaction):
            return await interaction.response.send_message("Administrator permission required.", ephemeral=True)
        if not await self._feature_guard(interaction, "role_reactions"):
            return
        try:
            mid = int(message_id)
            message = await interaction.channel.fetch_message(mid)
            await message.add_reaction(emoji)
            await self.bot.db["role_reactions"].update_one(
                {"guild_id": interaction.guild_id, "message_id": mid, "emoji": emoji},
                {"$set": {"role_id": role.id}}, upsert=True)
            await interaction.response.send_message(f"✅ {emoji} now grants {role.mention} on that message.", ephemeral=True)
        except (ValueError, discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
            await interaction.response.send_message(f"Could not configure reaction role: {str(exc)[:300]}", ephemeral=True)

    async def _apply_reaction_role(self, payload, add: bool):
        if payload.guild_id is None or self.bot.db is None:
            return
        if not await self._enabled(payload.guild_id, "role_reactions"):
            return
        emoji = str(payload.emoji)
        mapping = await self.bot.db["role_reactions"].find_one({
            "guild_id": payload.guild_id, "message_id": payload.message_id, "emoji": emoji})
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id) if guild else None
        role = guild.get_role(mapping["role_id"]) if guild and mapping else None
        if member and role and not member.bot:
            try:
                await (member.add_roles(role, reason="Self-service reaction role") if add
                       else member.remove_roles(role, reason="Self-service reaction role removed"))
            except discord.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self._apply_reaction_role(payload, True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self._apply_reaction_role(payload, False)

    @app_commands.command(name="ticket_open", description="Open a private support ticket")
    @app_commands.guild_only()
    async def ticket_open(self, interaction: discord.Interaction):
        if not await self._feature_guard(interaction, "tickets"):
            return
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        staff_role = guild.get_role(getattr(self.bot, "MODERATOR_ROLE_ID", 0))
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.defer(ephemeral=True)
        try:
            channel = await guild.create_text_channel(
                f"ticket-{interaction.user.name[:12]}".lower().replace(" ", "-"),
                overwrites=overwrites, reason=f"Support ticket opened by {interaction.user.id}")
            await channel.send(f"{interaction.user.mention} opened a ticket. Staff can help here; use `/ticket_close` when resolved.")
            await self._log(guild, "ticket_opened", {"channel_id": channel.id, "user_id": interaction.user.id})
            await interaction.followup.send(f"Your private ticket is {channel.mention}.", ephemeral=True)
        except discord.HTTPException as exc:
            await interaction.followup.send(f"Could not create ticket: {str(exc)[:300]}", ephemeral=True)

    @app_commands.command(name="ticket_close", description="Close and delete this ticket channel")
    @app_commands.guild_only()
    async def ticket_close(self, interaction: discord.Interaction):
        if not await self._feature_guard(interaction, "tickets"):
            return
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("ticket-"):
            return await interaction.response.send_message("Use this command inside a ticket channel.", ephemeral=True)
        is_staff = self._is_admin(interaction) or any(
            role.id == getattr(self.bot, "MODERATOR_ROLE_ID", None) for role in interaction.user.roles)
        if not is_staff and channel.permissions_for(interaction.user).manage_channels is False:
            # Ticket opener can close their own ticket if they have access to it.
            opener = channel.overwrites_for(interaction.user).view_channel
            if opener is not True:
                return await interaction.response.send_message("You cannot close this ticket.", ephemeral=True)
        await interaction.response.send_message("Closing ticket…", ephemeral=True)
        await self._log(interaction.guild, "ticket_closed", {"channel_id": channel.id, "closed_by": interaction.user.id})
        await channel.delete(reason=f"Ticket closed by {interaction.user.id}")

    @app_commands.command(name="review_actions", description="Report logged actions by actor over a recent time window")
    @app_commands.guild_only()
    @app_commands.describe(hours="Look back up to 168 hours", actor="Optional actor to filter by")
    async def review_actions(self, interaction: discord.Interaction,
                             hours: app_commands.Range[int, 1, 168], actor: discord.Member = None):
        if not self._is_admin(interaction):
            return await interaction.response.send_message("Administrator permission required.", ephemeral=True)
        if self.bot.db is None:
            return await interaction.response.send_message("MongoDB is required for action history.", ephemeral=True)
        query = {"guild_id": interaction.guild_id, "timestamp": {"$gte": datetime.now(timezone.utc) - timedelta(hours=hours)}}
        if actor:
            query["actor_id"] = actor.id
        rows = await self.bot.db["audit_events"].find(query).sort("timestamp", -1).to_list(length=50)
        lines = [f"• `{r['timestamp'].strftime('%Y-%m-%d %H:%M UTC')}` **{r['event']}** — {r.get('details', {})}" for r in rows]
        text = "\n".join(lines) if lines else "No recorded actions match that filter."
        await interaction.response.send_message(
            f"**Action report (last {hours}h, up to 50 records)**\n{text[:1700]}\n\nThis command reports observed events; it does not bulk-revert server changes.",
            ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove a member's active timeout")
    @app_commands.guild_only()
    async def untimeout(self, interaction: discord.Interaction, target: discord.Member, reason: str = "Timeout removed."):
        if not self._is_admin(interaction):
            return await interaction.response.send_message("Administrator permission required.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        try:
            await target.timeout(None, reason=reason[:500])
            await self._log(interaction.guild, "untimeout", {"target_id": target.id, "reason": reason[:500]}, interaction.user.id)
            await interaction.followup.send(f"✅ Removed timeout for {target.mention}.", ephemeral=True)
        except discord.HTTPException as exc:
            await interaction.followup.send(f"Could not remove timeout: {str(exc)[:300]}", ephemeral=True)

    @app_commands.command(name="unkick", description="Send a kicked user a one-use invite to rejoin")
    @app_commands.guild_only()
    async def unkick(self, interaction: discord.Interaction, user_id: str):
        if not self._is_admin(interaction):
            return await interaction.response.send_message("Administrator permission required.", ephemeral=True)
        try:
            user = await self.bot.fetch_user(int(user_id))
            channel = interaction.channel
            invite = await channel.create_invite(max_age=86400, max_uses=1, unique=True,
                                                 reason=f"Rejoin invite requested by {interaction.user.id}")
            await user.send(f"You have been invited to rejoin **{interaction.guild.name}**: {invite.url}")
            await self._log(interaction.guild, "unkick_reinvite_sent", {"target_id": user.id}, interaction.user.id)
            await interaction.response.send_message("✅ Sent a one-use, 24-hour rejoin invite by DM.", ephemeral=True)
        except (ValueError, discord.Forbidden, discord.HTTPException) as exc:
            await interaction.response.send_message(f"Could not send rejoin invite: {str(exc)[:300]}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(CommunityAdmin(bot))

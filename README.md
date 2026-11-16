# 🌌 Eternity — Discord moderation and community bot

Eternity is a modular `discord.py` bot with moderation commands, MongoDB-backed cases, AI responses, and optional community tools. Optional tools are **off by default** and configured per server.

## Optional community features

Use `/feature_toggle` to turn on one feature and `/feature_status` to inspect settings:

- **Anti-raid alerts**: records join bursts of at least five joins in 60 seconds; it does not automatically ban or kick members.
- **Audit logs and recovery snapshots**: records observed member, role, channel, and message-delete metadata. Deleted roles and supported text/voice/category channels get a MongoDB snapshot. `/restore_snapshot` can preview or restore them with administrator approval.
- **Reaction roles**: enable and use `/role_reaction_add` in the channel with the message ID, emoji, and role.
- **Tickets**: enable, then use `/ticket_open`; staff or the opener can use `/ticket_close`.

### Snapshot and restore limitations

The restore command is a high-impact operation and is restricted to server administrators/server owner; the hard-coded bot `ADMIN_IDS` are explicitly denied. A restore requires the audit feature to have captured the deleted role/channel event.

Restoration is not a true rollback: Discord gives recreated roles/channels new IDs. Role/channel references elsewhere must be updated. Channel permission overwrites referring to deleted roles or departments must be reattached manually after restore.

`/review_actions` reports up to 50 recorded events for up to 168 hours, optionally filtered by actor. It is report-only and does not bulk-revert arbitrary events.

## Moderation history

Moderation commands save cases to MongoDB with UTC timestamps, actor, target, reason, and case ID. `/unban` restores access for a banned user; `/untimeout` removes an active timeout. A kick cannot literally be undone, but `/unkick` can send a one-use invite to a removed member.

## Required Discord intents

Enable the Discord **Server Members Intent** and existing **Message Content Intent** in the developer portal. Grant only the permissions needed: Manage Channels for tickets/restoring channels, Manage Messages for purge, Timeout Members, Kick/Ban Members, View Audit Log for ownership attribution, and Embed Links for reports/logging.

## Rate limits and memory

Anti-raid uses a small rolling 60-second in-memory join window. There are no polling jobs. The bot does not mass-ban users or attempt to evade Discord rate limits; do not loop bulk restore actions. Discord rate limits and permission hierarchy still apply.

## Run and synchronize commands

Install dependencies from `requirements.txt`; configure `ETERNITY_TOKEN` (or `DISCORD_TOKEN`), `GEMINI_API_KEY`, and optionally `MONGO_URI`; then run `python Eternity.py`. Use owner-only `?sync` to push slash commands to the current server, and `?sync global` to sync globally.

## Command reference

Most administration and utility actions are slash commands, and they are made available after the bot starts and the command tree is synced.

### Prefix / owner commands

- `?ping` — Check the bot's current latency in milliseconds.
- `?sync` — Sync slash commands to the current guild.
- `?sync global` — Sync slash commands globally.
- `?sync clear` — Clear guild-specific command registrations before resyncing.

### AI and utility commands

- `/help` — Open the help menu and browse the available command groups.
- `/ask <question>` — Ask Eternity to respond using the configured Gemini AI model.
- `/behave <target> <rule>` — Send a conduct reminder to a member in the current guild.
- `/userinfo [target]` — Display a member's account info, join date, and roles.
- `/avatar [target]` — Show a member's avatar in an embed.
- `/afk [reason]` — Mark yourself as AFK; tagged users receive an AFK notice automatically.
- `/report <target> <reason>` — Submit a moderation report that is logged and sent to the configured moderation log channel if available.

### Moderation commands

- `/setlogchannel <channel>` — Set the guild moderation log channel.
- `/warn <target> <reason>` — Issue a formal warning and log it.
- `/warnings <target>` — View a member's recent warning history.
- `/timeout <target> <minutes> <reason>` — Timeout a member for up to 28 days.
- `/unmute <target> [reason]` — Remove an active timeout.
- `/kick <target> [reason]` — Kick a member and record the case.
- `/ban <target> [reason]` — Ban a member and record the case.
- `/unban <user_id> [reason]` — Unban a user by Discord ID.
- `/clear <amount>` — Delete a number of recent messages from the current channel.
- `/add_log <topic> <reason> [target]` — Save a custom moderation/log record in MongoDB.
- `/browse_categories` — Browse all stored moderation categories through a dropdown.
- `/search_logs <topic> [target] [is_public]` — Search recent records for a topic and optional target user.
- `/copy <message_input> [reply_text] [target_channel]` — Admin-only helper to clone or forward text/contents anonymously.

### Community and optional feature commands

- `/feature_toggle <feature> <enabled>` — Enable or disable a guild-scoped optional feature.
- `/feature_status` — Display the enabled/disabled status of all optional features.
- `/role_reaction_add <message_id> <emoji> <role>` — Attach an emoji-to-role mapping to an existing message.
- `/ticket_open` — Open a private support ticket channel for the user.
- `/ticket_close` — Close and delete the current ticket channel.
- `/review_actions <hours> [actor]` — Review recent audit log events in a time window.
- `/restore_snapshot <event_id> [confirm]` — Preview or restore a deleted role/channel snapshot. Requires admin/owner privileges.
- `/untimeout <target> [reason]` — Remove an active timeout from a member and log the event.
- `/unkick <user_id>` — Send a one-use invite to a kicked user so they can rejoin.

### Automatic event-driven behavior

- The bot watches for messages containing `Eternal` or `Victory` and adds a `💠` reaction.
- If a message is exactly `protect the faction` or `?cosmicgif`, it posts a themed cosmic GIF link.
- When the anti-raid and audit features are enabled, the bot logs join bursts, role changes, channel creation/deletion, role deletion, member leave, and deleted messages.

## Resource use

The optional features are event/command-driven and use bounded in-memory state, intended for a 512 MB host. Actual memory depends on the existing Python, Discord, and AI dependencies and workload.

## License

This project is licensed under the MIT License. See `LICENSE` for details.

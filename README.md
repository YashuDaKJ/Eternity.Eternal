# 🌌 Eternity — Discord moderation and community bot

Eternity is a modular `discord.py` bot with moderation commands, MongoDB-backed cases, AI responses, and optional community tools. Optional tools are **off by default** and are configured per server.

## Optional community features

After inviting the bot with the required permissions and syncing slash commands, a server administrator can use `/feature_toggle` to turn on one feature at a time, and `/feature_status` to inspect settings:

- **Anti-raid alerts**: records join bursts of at least five joins in 60 seconds. It only alerts/logs; it does not automatically ban or kick members.
- **Audit logs**: stores observed member joins/leaves, role changes, channel changes, and deleted-message metadata in MongoDB. Deleted message contents are deliberately not stored.
- **Reaction roles**: enable the feature, then run `/role_reaction_add` in the channel containing the target message with the message ID, emoji, and role. Members can add/remove the role using that reaction.
- **Tickets**: enable the feature, then members use `/ticket_open`; staff or the opener can use `/ticket_close` inside the private ticket channel.

`/review_actions` reports up to 50 recorded events for a selected period (maximum 168 hours), optionally filtered by actor. Records only exist for events observed after the feature and bot are running. Configure `/setlogchannel` for human-readable audit notifications.

## Action history and reversals

Moderation cases already written by moderation commands are saved in MongoDB with UTC timestamps, actor, target, reason, and case ID. The community cog additionally stores observed audit metadata in `audit_events`.

`/unban` restores access for a banned user. `/untimeout` removes an active timeout. A kick cannot literally be undone: `/unkick` sends the user a one-use invite that expires after 24 hours, if the bot can DM them.

A broad “undo everything an actor did in the last X hours” is intentionally not automated. Discord does not offer a universal rollback API; deleted messages may have no recoverable body, deleted channels/roles may be unrecoverable, and replaying permissions or role changes blindly can lock people out or expose private channels. `/review_actions` is report-only. Review the report and use targeted, explicit moderation/configuration commands to make corrections.

## MongoDB setup

Set `MONGO_URI` to a MongoDB connection string. The bot uses database `eternal_faction_db` and collections including `moderation_logs`, `counters`, `guild_settings`, `audit_events`, and `role_reactions`. Restrict the database user to this database, keep credentials in your host's secret manager, and do not commit secrets. If MongoDB is unavailable, persistent features and their settings will not work; the bot does not silently pretend they are saved.

The bot needs the Discord **Server Members Intent** for member events and **Message Content Intent** for existing message/AI behavior. For channel and role management, grant only the needed permissions (View/Send Messages, Manage Channels for tickets, Manage Roles for role reactions, and View Audit Log only if you later add audit-log attribution). Keep the bot role above roles it must assign.

## Anti-raid and rate limits

The anti-raid handler uses a small in-memory rolling 60-second join window and a threshold alert; it does not issue mass punishments. This avoids burst bans and unnecessary Discord API calls. Discord may still rate-limit any bot that sends too many requests, so avoid adding tight loops or repeated bulk actions. The bot should space administrative actions and stop/retry on HTTP 429 responses rather than attempting to bypass platform limits.

## Run and synchronize commands

Install dependencies from `requirements.txt`, configure `ETERNITY_TOKEN` (or `DISCORD_TOKEN`), `GEMINI_API_KEY`, and optionally `MONGO_URI`, then run `python Eternity.py`. Use the owner-only `?sync` command to publish slash commands. Feature configuration requires MongoDB.

## Resource use

The optional features add no background polling jobs. Anti-raid state is limited to recent joins; database queries are event- or command-driven. This is designed to remain lightweight for a 512 MB host, though actual usage depends on the existing AI/Discord dependencies and workload.

# 🌌 Eternity — Discord moderation and community bot

Eternity is a modular `discord.py` bot with moderation commands, MongoDB-backed cases, AI responses, and optional community tools. Optional tools are **off by default** and configured per server.

## Optional community features

Use `/feature_toggle` to turn on one feature and `/feature_status` to inspect settings:

- **Anti-raid alerts**: records join bursts of at least five joins in 60 seconds; it does not automatically ban or kick members.
- **Audit logs and recovery snapshots**: records observed member, role, channel, and message-delete metadata. Deleted roles and supported text/voice/category channels get a MongoDB snapshot. `/review_actions` shows event IDs. `/restore_snapshot` first previews a snapshot, then recreates it only when explicitly invoked again with `confirm: true`.
- **Reaction roles**: enable and use `/role_reaction_add` in the channel with the message ID, emoji, and role.
- **Tickets**: enable, then use `/ticket_open`; staff or the opener can use `/ticket_close`.

### Snapshot and restore limitations

The restore command is a high-impact operation and is restricted to server administrators/server owner; the hard-coded bot `ADMIN_IDS` are explicitly denied. A restore requires the audit feature to have been enabled at deletion time, MongoDB availability, and the bot to have the needed permissions. For best-effort attribution, grant **View Audit Log**. If Discord audit entries are unavailable, the actor is recorded as unknown.

Restoration is not a true rollback: Discord gives recreated roles/channels new IDs. Role/channel references elsewhere must be updated. Channel permission overwrites referring to deleted roles or departed members cannot be recreated and are skipped. Category placement and role position are approximate. Only roles and text, voice, and category channels are automatically restorable; other types are logged as metadata only. Deleted messages and message history are not restored. Review the preview before confirming, and never rely on snapshots as the only backup.

`/review_actions` reports up to 50 recorded events for up to 168 hours, optionally filtered by actor. It is report-only and does not bulk-revert arbitrary events.

## Moderation history

Moderation commands save cases to MongoDB with UTC timestamps, actor, target, reason, and case ID. `/unban` restores access for a banned user; `/untimeout` removes an active timeout. A kick cannot literally be undone: `/unkick` sends the user a one-use invite that expires after 24 hours, if the bot can DM them.


Enable the Discord **Server Members Intent** and existing **Message Content Intent** in the developer portal. Grant only the permissions needed: Manage Channels for tickets/restoring channels, Manage Roles for reaction roles/role restore, and View Audit Log for action attribution. Keep the bot's role above roles it must manage.

## Rate limits and memory

Anti-raid uses a small rolling 60-second in-memory join window. There are no polling jobs. The bot does not mass-ban users or attempt to evade Discord rate limits; do not loop bulk restore actions. Discord can still return HTTP 429, so operations should be performed individually and retried only after the indicated delay.

## Run and synchronize commands

Install dependencies from `requirements.txt`; configure `ETERNITY_TOKEN` (or `DISCORD_TOKEN`), `GEMINI_API_KEY`, and optionally `MONGO_URI`; then run `python Eternity.py`. Use owner-only `?sync` to publish slash commands.

## Resource use

The optional features are event/command-driven and use bounded in-memory state, intended for a 512 MB host. Actual memory depends on the existing Python, Discord, and AI dependencies and workload.

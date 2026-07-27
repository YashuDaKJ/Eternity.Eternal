<p align="center">
  <img src="https://cdn.discordapp.com/attachments/1492172037500698758/1528034472929395029/Eternity_.png?ex=6a5cd47f&is=6a5b82ff&hm=d38264d04144342cb643c85d9cc11d3102dd49340724dda0e68fdc657b5a369f&" alt="Eternity Logo" width="180"/>
</p>

# 🌌 Eternity — Guild Moderation & Protection Core

**Eternity** is an active security and moderation Discord bot built explicitly to safeguard the **Eternal** faction server. Designed with modern asynchronous Python practices, it combines standard administrative command sets with deep AI-driven conversational context using Google's **Gemini 2.5 Flash** API.

The project is structured with a modular Cogs setup, allowing isolated feature maintenance across moderation, utilities, and automated event triggers.

---

## 🛠️ System Overview & Architecture

* **Modular Cogs Architecture:** Decoupled functional modules (`utilities`, `moderation`, `reactions`) to keep the main event loop clean and maintainable.
* **Contextual AI Integration:** Generates contextual responses based on dynamic message histories via Gemini 2.5 Flash.
* **Direct Vision Processing:** Accepts direct image attachments and media assets within conversational channels for automated scanning and responses.
* **Dual-Command Interface:** Full support for modern Discord Slash (`/`) Application Commands along with legacy Message Prefix (`?`) fallbacks.
* **Continuous Uptime Stack:** Embedded lightweight Web Server (Flask) paired with a background heartbeat thread to prevent container sleeping on hosted platforms like Render.

---

## 🛡️ Command Matrix

Eternity operates primary operations via Discord Slash Commands (`/`).

### 🌌 Utilities & Query Intelligence
| Command | Parameters | Description |
| :--- | :--- | :--- |
| `/help` | None | Displays an interactive interface listing all operational parameters. |
| `/ask` | `question` | Queries the core AI model for direct responses and faction assistance. |
| `?ping` | None | Measures direct gateway latency between the bot framework and Discord's servers. |

### 🛑 Administrative & Moderation Commands
| Command | Parameters | Hierarchy / Auth | Description |
| :--- | :--- | :--- | :--- |
| `/warn` | `target`, `reason` | Mod / Admin | Issues an official violation warning notice to a specified member. |
| `/timeout`| `target`, `minutes`, `reason` | Mod / Admin | Applies temporary communication suppression (Mute) to an element. |
| `/clear` | `amount` | Mod / Admin | Purges specified recent message frames (1–100 limit). |
| `/kick` | `target`, `reason` | Mod / Admin | Removes an element from the active server footprint. |
| `/ban` | `target`, `reason` | Admin Only | Permanently terminates a disruptive member's network connection. |
| `/unban` | `user_id`, `reason` | Admin Only | Restores network access rights to a previously banned Discord Snowflake ID. |
| `/behave` | `target`, `rule` | Admin Only | Issues an explicit behavior directive to an individual user. |

---

## ⚡ Deployment & Resource Specifications

Eternity is optimized to run efficiently with minimal server footprint on cloud environments (e.g., Render, Railway, VPS) or local environments.

### System Requirements
| Resource | Minimum Requirement | Recommended Specification |
| :--- | :--- | :--- |
| **CPU** | 0.1 vCPU (Shared) | 0.5 vCPU |
| **RAM** | 256 MB | 512 MB |
| **Disk Space** | 100 MB | 500 MB |
| **Runtime Environment** | Python 3.10+ | Python 3.11+ |

---

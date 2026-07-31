<p align="center">
  <img src="https://cdn.discordapp.com/attachments/1492172037500698758/1528034472929395029/Eternity_.png?ex=6a5cd47f&is=6a5b82ff&hm=d38264d04144342cb643c85d9cc11d3102dd49340724dda0e68fdc657b5a369f&" alt="Eternity Logo" width="180"/>
</p>

# 🌌 Eternity — Advanced Faction Security & Moderation Core

**Eternity** is an enterprise-grade automated security, intelligence, and moderation infrastructure engineered specifically to protect and govern the **Eternal** faction ecosystem. Built on robust asynchronous Python architectures, Eternity fuses deterministic moderation protocols with deep contextual intelligence powered by Google’s **Gemini 2.5 Flash** API.

The system relies on a dynamic, modular Cogs framework (`moderation.py`, `utilities.py`, `reactions.py`) to guarantee low-latency execution, structural isolation, and 24/7 autonomous uptime.

---

## 🛠️ Architectural Overview

* **Modular Cogs Design:** Decoupled functional logic maintaining a clean, scalable event loop across utility, enforcement, and reaction matrices.
* **Contextual Neural Intelligence:** Leverages Gemini 2.5 Flash for dynamic conversation handling, policy interpretation, and automated threat reasoning.
* **Native Vision & Media Processing:** Direct ingestion and scanning of image assets and multimedia attachments within active operational channels.
* **Interactive UI Elements:** Features fully interactive Discord Dropdown Menus (`discord.ui.Select`) for streamlined command navigation.
* **Optimized Command Trees:** Synchronized dual-interface supporting modern Discord Application Slash Commands (`/`) alongside fallback administrative prefixes (`?`). Features built-in duplicate-clearing technology (`?sync clear`).
* **Continuous Uptime Framework:** Embedded lightweight Flask web server integrated with a background heartbeat thread to maintain 24/7 container liveness on cloud hosting environments.

---

## 🛡️ Operational Command Matrix

Operations are primarily executed via secure Discord Slash Commands (`/`), backed by administrative control utilities.

### ⚙️ Core Utilities & Player Networking
| Command | Parameters | Description |
| :--- | :--- | :--- |
| `/help` | None | Deploys an interactive UI interface detailing active operational parameters. |
| `/ask` | `question` | Queries the core neural model for direct strategic response or intelligence. |
| `/userinfo` | `[target]` | Extracts and displays the digital footprint and role hierarchy of a node. |
| `/avatar` | `[target]` | Fetches the high-resolution profile imagery of a target entity. |
| `/afk` | `[reason]` | Registers the user's status as Away From Keyboard on the network. |
| `/report` | `target`, `reason` | Submits a formal, logged player violation report to the administration. |
| `?ping` | None | Evaluates real-time gateway latency between the framework and Discord clusters. |

### 🚨 Administrative & Moderation Protocols
| Command | Parameters | Auth Level | Description |
| :--- | :--- | :--- | :--- |
| `/warn` | `target`, `reason` | Moderator+ | Issues a formal structural violation warning to a designated member. |
| `/timeout`| `target`, `minutes`, `reason` | Moderator+ | Enforces temporary communication suppression (Mute) on an element. |
| `/clear` | `amount` | Moderator+ | Purges specified message frames from the active channel buffer (1–100). |
| `/kick` | `target`, `reason` | Moderator+ | Evicts a non-compliant element from the server environment. |
| `/ban` | `target`, `reason` | Administrator | Permanently revokes network and server access for a high-risk entity. |
| `/unban` | `user_id`, `reason` | Administrator | Restores access authorization to a previously archived Snowflake ID. |
| `/behave` | `target`, `rule` | Administrator | Directs explicit behavioral compliance protocol toward an individual. |
| `?copy` | `message` | Administrator | Covertly broadcasts an exact text string via the bot's system node. |
| `?sync` | `[clear]` | Administrator | Reconciles and synchronizes application command trees globally. |

---

## ⚡ Deployment & Resource Specifications

Eternity is optimized for ultra-lean cloud execution, guaranteeing high efficiency with minimal resource consumption.

### Minimum System Footprint
| Resource Metric | Specification |
| :--- | :--- |
| **CPU Allocation** | 0.1 vCPU (Shared) / 0.5 vCPU Recommended |
| **Memory (RAM)** | 256 MB (512 MB Recommended) |
| **Storage** | 100 MB Operational Footprint |
| **Runtime Environment**| Python 3.11+ (Asynchronous Event Loop) |


💠Protecting Eternal from a long time💠

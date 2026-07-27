<p align="center">
  <img src="https://cdn.discordapp.com/attachments/1492172037500698758/1528034472929395029/Eternity_.png?ex=6a5cd47f&is=6a5b82ff&hm=d38264d04144342cb643c85d9cc11d3102dd49340724dda0e68fdc657b5a369f&" alt="Eternity Logo" width="180"/>
</p>

# 🌌 Eternity — Guild Moderation & Protection Core

**Eternity** is an active security and moderation Discord bot built explicitly to safeguard the **Eternal** faction server. Designed with modern asynchronous Python practices, it combines standard administrative command sets with deep AI-driven conversational context using Google's **Gemini 2.5 Flash** API.

The project is structured with a modular Cogs setup, allowing isolated feature maintenance across moderation, utilities, and automated event triggers.

---

## 🛠️ System Overview & Architecture

* **Modular Cogs Architecture:** Decoupled functional modules (`utilities`, `moderation`, `reactions`) to keep the main event loop clean and maintainable.
* **Contextual AI Integration:** Generates contextual responses based on internal faction parameters and dynamic message histories via Gemini 2.5 Flash.
* **Direct Vision Processing:** Accepts direct image attachments and media assets within conversational channels for automated scanning and responses.
* **Dual-Command Interface:** Full support for modern Discord Slash (`/`) Application Commands along with legacy Message Prefix (`?`) fallbacks.
* **Continuous Uptime Stack:** Embedded lightweight Web Server (Flask) paired with a background heartbeat thread to prevent container sleeping on hosted platforms like Render.

---

## 📁 Repository Structure

```text
├── Eternity.py         # Application entry point, client initialization, and core events
├── core_data.py        # System instructions, personality prompts, and faction database
├── cogs/
│   ├── utilities.py    # General interaction nodes (/help, /ask, /behave)
│   ├── moderation.py   # Administrative enforcement (/warn, /timeout, /clear, /kick, /ban, /unban)
│   └── reactions.py    # Background event listeners, GIF parsing, and keyword reactions
└── requirements.txt    # Application dependencies

<h1 align="center">Restricted Content Downloader Telegram Bot</h1>

<p align="center">
  <a href="https://github.com/mefadratulku-pixel/TelegramPrivateBot/stargazers"><img src="https://img.shields.io/github/stars/mefadratulku-pixel/TelegramPrivateBot?color=blue&style=flat" alt="GitHub Repo stars"></a>
  <a href="https://github.com/mefadratulku-pixel/TelegramPrivateBot/issues"><img src="https://img.shields.io/github/issues/mefadratulku-pixel/TelegramPrivateBot" alt="GitHub issues"></a>
  <a href="https://github.com/mefadratulku-pixel/TelegramPrivateBot/pulls"><img src="https://img.shields.io/github/issues-pr/mefadratulku-pixel/TelegramPrivateBot" alt="GitHub pull requests"></a>
  <a href="https://github.com/mefadratulku-pixel/TelegramPrivateBot/network/members"><img src="https://img.shields.io/github/forks/mefadratulku-pixel/TelegramPrivateBot?style=flat" alt="GitHub forks"></a>
</p>

<p align="center">
  <em>A blazing-fast, next-generation restricted content downloader for Telegram. Fully native on Windows — zero Docker required. Download restricted photos, videos, audio files, or documents from Telegram private chats or channels, and copy text messages from posts.</em>
</p>

## ✨ Power Features

- ⚡ **32 parallel chunk transmissions** — downloads parts concurrently from Telegram DC servers at maximum possible bandwidth.
- 🖥️ **Fully native on Windows** — zero Docker required. 1-click run with `login.cmd` / `start.cmd` / `stop.cmd`.
- ⌨️ **Interactive Terminal Command Center (CLI)** — paste links or run commands right inside the terminal, with a cyberpunk neon dashboard.
- 🍬 **Animated progress tracker** — Pac-Man style animated tracker in both Telegram and terminal.
- 🔍 **Zero-byte smart duplicate detector** — checks SQLite history and local disk *before* downloading; existing files are skipped without wasting bandwidth.
- 🌐 **Telegram Data Center ping meter** — live TCP ping to all Telegram Data Centers.
- 📱 **Interactive Telegram dashboard** — quick inline buttons for Stats, Clean Temp, Cancel All, and Logs.
- 📥 **Multiple download methods** — single post, media groups, batch ranges, bulk paste (parallel), or simply forward a restricted post to the bot.
- 🗂️ **Organized storage** — all media auto-organized by channel and type under `SavedMedia/`.

## Requirements

Before you begin, ensure you have met the following requirements:

- Windows with Python installed (no Docker needed)
- A Telegram bot token (you can get one from [@BotFather](https://t.me/BotFather) on Telegram)
- API ID and Hash: You can get these by creating an application on [my.telegram.org](https://my.telegram.org)
- Python dependencies: install with `pip install -r requirements.txt` (`pyrofork`, `pyleaves`, `tgcrypto`, and `ffmpeg` — ffmpeg must be on PATH)

## Configuration

1. Copy `config.env.sample` to `config.env` (or run `login.cmd` once — it saves your session automatically).
2. Replace the placeholders for `API_ID`, `API_HASH`, `SESSION_STRING`, and `BOT_TOKEN` with your actual values:
   - **`API_ID`**: Your API ID from [my.telegram.org](https://my.telegram.org).
   - **`API_HASH`**: Your API Hash from [my.telegram.org](https://my.telegram.org).
   - **`SESSION_STRING`**: Your Pyrogram session string (generated on first `login.cmd` run).
   - **`BOT_TOKEN`**: The token you obtained from [@BotFather](https://t.me/BotFather).

3. Optional performance settings (in `config.py`):
   - **`MAX_CONCURRENT_DOWNLOADS`**: Number of simultaneous downloads (default: 3)
   - **`BATCH_SIZE`**: Number of posts to process in parallel during batch downloads (default: 10)
   - **`FLOOD_WAIT_DELAY`**: Delay in seconds between batch groups to avoid flood limits (default: 3)

## 🚀 Quick Start (1-Click Run)

### 1. Connect your Telegram account (first time)
Double-click **`login.cmd`**
- Enter your phone number with country code (e.g. `+8801XXXXXXXXX`).
- Type the verification code sent to your Telegram app.
- Your session is automatically authenticated and saved into `config.env`.

### 2. Start the bot
Double-click **`start.cmd`**
- Launches the cyberpunk neon dashboard.
- Shows live Telegram Data Center ping and connectivity.
- Starts the interactive Terminal Command Center.
- Bot is instantly online!

### 3. Stop the bot
Double-click **`stop.cmd`**, or simply type `exit` in the bot's terminal window.

## 🎯 Download Methods

### From the terminal (CLI)
Paste links or run commands directly:
```text
⚡ [RestrictedDL] > https://t.me/c/123456789/10
⚡ [RestrictedDL] > https://t.me/c/123456789/10-35
⚡ [RestrictedDL] > ping
⚡ [RestrictedDL] > stats
⚡ [RestrictedDL] > cleanup
```

### From Telegram chat
- **Single post:** just paste any Telegram link (no need to type `/dl`).
- **Batch range:** `https://t.me/c/123456789/10-50` (hyphen format), `link1 link2`, or `/bdl link1 link2`.
- **Bulk paste:** paste 5, 10, or 20 links in one message — the bot downloads them in parallel.
- **Forward:** simply forward any restricted post directly to the bot.

## 📟 Bot Commands

- **`/start`** – Welcome message and brief introduction.
- **`/help`** – Detailed instructions and examples.
- **`/dl <link>`** – Download media from a single post (or just paste the link).
- **`/bdl <link1> <link2> ...`** – Batch-download multiple posts.
- **`/ping`** (or **`/dc`**) – Live ping to Telegram Data Centers.
- **`/proxy`** – Proxy settings.
- **`/stats`** – Current status (uptime, disk, memory, network, CPU).
- **`/logs`** – Download the bot's log file.
- **`/killall`** – Cancel all pending downloads.
- **`/cleanup`** – Remove temporary downloaded files from the server.

> **Note:** Make sure that your user session is a member of the source chat or channel before downloading.

## 📁 Storage Location

All media files are organized by channel and type inside:
```text
SavedMedia/
  ├── <channel>/
  │     ├── Videos/
  │     ├── Photos/
  │     ├── Documents/
  │     └── Audio/
```

## Author & Credits

- **Maintainer:** [Mefaduzzaman Ratul](https://github.com/mefadratulku-pixel) — further developed with new features and improvements.
- **Original author:** [Bisnu Ray](https://github.com/bisnuray) — this project is based on his [RestrictedContentDL](https://github.com/bisnuray/RestrictedContentDL).

> **Note**: If you found this repo helpful, please star it and share with proper credit!

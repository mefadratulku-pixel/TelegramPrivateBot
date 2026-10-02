# ⚡ RestrictedContentDL — Ultimate Telegram Downloader

A blazing-fast, next-generation restricted content downloader for Telegram. Fully native on Windows — zero Docker required.

---

## 🚀 Quick Start (1-Click Run)

### 1. Connect Your Telegram Account (First Time / New Session)
Double-click:
```cmd
login.cmd
```
- Enter your phone number with country code (e.g. `+8801XXXXXXXXX`).
- Type the 5-digit verification code sent to your Telegram app.
- Your session is automatically authenticated and saved into `config.env`!

### 2. Start the Bot
Double-click:
```cmd
start.cmd
```
- Launches the Cyberpunk neon dashboard.
- Displays live Telegram Data Center (DC) ping and connectivity.
- Starts the **Interactive Terminal Command Center (CLI)**.
- Bot is instantly online!

### 3. Stop the Bot
Double-click:
```cmd
stop.cmd
```
Or simply type `exit` in the bot's terminal window.

---

## 🎯 Super-Easy Download Methods

### Method 1: Directly from Terminal (Next-Gen CLI)
You can directly paste links or run commands right inside the terminal:
```text
⚡ [RestrictedDL] > https://t.me/c/123456789/10
⚡ [RestrictedDL] > https://t.me/c/123456789/10-35
⚡ [RestrictedDL] > ping
⚡ [RestrictedDL] > stats
⚡ [RestrictedDL] > cleanup
```

### Method 2: In Telegram Chat (@mydloaderbot)
- **Single Post:** Just paste any Telegram link (no need to type `/dl`).
- **Batch Range:**
  - `https://t.me/c/123456789/10-50` (hyphen format)
  - `link1 link2`
  - `/bdl link1 link2`
- **Bulk Paste:** Paste 5, 10, or 20 links in one message — bot downloads them in parallel!
- **Forward:** Simply forward any restricted post directly to the bot.

---

## ✨ Power Features Included

1. **⚡ 32 Parallel Chunk Transmissions:**
   Downloads parts concurrently from Telegram DC servers at maximum possible bandwidth.
2. **🍬 Arch Linux "ILoveCandy" (Pac-Man) Tracker:**
   Animated Pac-Man (`👻 ━━━━ᗧ • • • • 🍒`) eating candies in both Telegram and Terminal!
3. **🔍 Zero-Byte Smart Duplicate Detector:**
   Checks SQLite history and local disk **before** downloading. Existing files are skipped in 0.001s without wasting a single byte of bandwidth!
4. **🌐 Telegram Data Center Ping Meter (`/ping` or `/dc`):**
   Live TCP ping to all 5 Telegram Data Centers (Miami, Amsterdam, Singapore).
5. **📱 Interactive Telegram Dashboard:**
   Quick inline buttons for Stats, Clean Temp, Cancel All, and Logs.

---

## 📁 Storage Location
All media files are organized by channel and type inside:
```text
SavedMedia/
  ├── <channel_name>/
  │     ├── Videos/
  │     ├── Photos/
  │     ├── Documents/
  │     └── Audio/
```

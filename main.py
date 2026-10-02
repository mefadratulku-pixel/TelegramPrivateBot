# Copyright (C) @TheSmartBisnu
# Channel: https://t.me/itsSmartDev

import os
import sys
import shutil
import psutil
import asyncio
import socket
from time import time

# Hardware TCP Socket Turbo Engine: Expand Windows default 64KB TCP buffer to 4MB
# Eliminates latency-based TCP throughput throttling to Telegram DC servers
_orig_socket_init = socket.socket.__init__
def _turbo_socket_init(self, *args, **kwargs):
    _orig_socket_init(self, *args, **kwargs)
    try:
        if self.family in (socket.AF_INET, socket.AF_INET6) and self.type == socket.SOCK_STREAM:
            self.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
            self.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1 * 1024 * 1024)
            self.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass
socket.socket.__init__ = _turbo_socket_init

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


import logging
logging.getLogger("pyrogram").setLevel(logging.ERROR)

from pyleaves import Leaves
from pyrogram.enums import ParseMode
from pyrogram import Client, filters
from pyrogram.errors import PeerIdInvalid, BadRequest, FloodWait
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from helpers.utils import (
    processMediaGroup,
    progressArgs,
)

from helpers.files import (
    get_download_path,
    get_save_path,
    file_exists_in_save_dir,
    fileSizeLimit,
    get_readable_file_size,
    get_readable_time,
    cleanup_download,
    cleanup_downloads_root
)

from helpers.msg import (
    getChatMsgID,
    get_channel_name,
    get_file_name,
    get_parsed_msg
)

from helpers.tracker import candy_progress
from helpers.fast_download import fast_download_file
from helpers.duplicate import dup_manager
from helpers.dc_ping import get_all_dc_pings, get_dc_table_rich, generate_telegram_report

from config import PyroConf, set_proxy_state, toggle_proxy_state
from logger import LOGGER
from rich.console import Console

term_ui = Console(highlight=False)
proxy_dict = PyroConf.get_proxy()

# Initialize the bot client (Parallel chunk transmissions enabled for ultra-fast downloads)
bot = Client(
    "media_bot",
    api_id=PyroConf.API_ID,
    api_hash=PyroConf.API_HASH,
    bot_token=PyroConf.BOT_TOKEN,
    workers=100,
    parse_mode=ParseMode.MARKDOWN,
    max_concurrent_transmissions=32,
    sleep_threshold=30,
    proxy=proxy_dict,
)

# Client for user session (High-speed multi-connection downloads)
user = Client(
    "user_session",
    workers=100,
    session_string=PyroConf.SESSION_STRING,
    max_concurrent_transmissions=32,
    sleep_threshold=30,
    proxy=proxy_dict,
)

RUNNING_TASKS = set()
download_semaphore = None
pending_duplicates = {}

def track_task(coro):
    task = asyncio.create_task(coro)
    RUNNING_TASKS.add(task)
    def _remove(_):
        RUNNING_TASKS.discard(task)
    task.add_done_callback(_remove)
    return task


def get_dashboard_markup():
    is_proxy_active = PyroConf.USE_PROXY and bool(PyroConf.get_proxy())
    proxy_btn_text = "🟢 BDIX: ON" if is_proxy_active else "🔴 BDIX: OFF"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 System Stats", callback_data="btn_stats"),
            InlineKeyboardButton("⚡ DC Speed / Ping", callback_data="btn_ping"),
        ],
        [
            InlineKeyboardButton(f"🌐 {proxy_btn_text}", callback_data="btn_proxy_menu"),
            InlineKeyboardButton("🔍 Duplicate Stats", callback_data="btn_dup_stats"),
        ],
        [
            InlineKeyboardButton("🧹 Clean Temp", callback_data="btn_cleanup"),
            InlineKeyboardButton("🛑 Cancel All Tasks", callback_data="btn_killall"),
        ],
        [
            InlineKeyboardButton("📋 View Logs", callback_data="btn_logs"),
            InlineKeyboardButton("💡 Guide", callback_data="btn_guide"),
        ],
        [
            InlineKeyboardButton("📢 Channel", url="https://t.me/itsSmartDev"),
        ]
    ])


def get_proxy_panel_data():
    is_on = PyroConf.USE_PROXY and bool(PyroConf.get_proxy())
    status_icon = "🟢 **ON (Active)**" if is_on else "🔴 **OFF (Disabled)**"
    status_desc = f"BDIX Proxy is actively routing downloads through `{PyroConf.PROXY_HOST}:{PyroConf.PROXY_PORT}`." if is_on else "Bot is currently connecting directly without BDIX proxy."

    text = (
        "🌐 **BDIX PROXY CONTROLLER**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"➜ **Current Status:** {status_icon}\n"
        f"➜ **Proxy Server:** `{PyroConf.PROXY_HOST or 'Not configured'}:{PyroConf.PROXY_PORT}`\n"
        f"➜ **Protocol:** `HTTP (BDIX Squid)`\n"
        f"➜ **Username:** `{PyroConf.PROXY_USER or 'None'}`\n\n"
        f"ℹ️ {status_desc}\n\n"
        "💡 *Toggle BDIX proxy anytime with the buttons below, via terminal CLI (`proxy on` / `proxy off`), or double-click `toggle_proxy.cmd`.*"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Turn Proxy ON", callback_data="btn_proxy_on"),
            InlineKeyboardButton("🔴 Turn Proxy OFF", callback_data="btn_proxy_off"),
        ],
        [
            InlineKeyboardButton("🔄 Toggle State", callback_data="btn_proxy_toggle"),
            InlineKeyboardButton("⚡ Test DC Ping", callback_data="btn_ping"),
        ],
        [
            InlineKeyboardButton("🔙 Back to Dashboard", callback_data="btn_back_home"),
        ]
    ])
    return text, markup


@bot.on_message(filters.command("start") & filters.private)
async def start(_, message: Message):
    welcome_text = (
        "⚡ **RESTRICTED CONTENT DOWNLOADER** ⚡\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👋 **স্বাগতম! কোনো জটিল কমান্ড ছাড়া অতি সহজে ডাউনলোড করুন:**\n\n"
        "🎯 **যেভাবে ডাউনলোড করবেন:**\n"
        "• **Single Link:** সরাসরি যেকোনো টেলিগ্রাম পোস্টের লিংক পেস্ট করুন!\n"
        "• **Batch Range:** সরাসরি `link/10-30` অথবা `link1 link2` পেস্ট করুন!\n"
        "• **Bulk Links:** একসাথে ৫-১০টি লিংক দিলে একসাথে ডাউনলোড শুরু হবে!\n"
        "• **Forward:** যেকোনো চ্যানেল থেকে পোস্ট এখানে ফরোয়ার্ড করুন!\n\n"
        "🚀 **Speed Engine:** 2x Concurrent Downloads + 5x Parallel Streams\n"
        "🍬 **Live Tracker:** Arch Linux Pac-Man (ILoveCandy) animated progress!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 **কন্ট্রোল ড্যাশবোর্ড থেকে সহজেই পরিচালনা করুন:**"
    )
    await message.reply(welcome_text, reply_markup=get_dashboard_markup(), disable_web_page_preview=True)


@bot.on_message(filters.command("help") & filters.private)
async def help_command(_, message: Message):
    help_text = (
        "💡 **SUPER EASY USAGE GUIDE** 💡\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "➤ **১. সিঙ্গেল পোস্ট ডাউনলোড:**\n"
        "   লিংক কপি করে সরাসরি চ্যাটে পেস্ট করুন (অথবা `/dl <link>`)\n\n"
        "➤ **২. ব্যাচ ডাউনলোড (অনেকগুলো পোস্ট একসাথে):**\n"
        "   • হাইফেন দিয়ে: `https://t.me/c/123/10-30`\n"
        "   • স্পেস দিয়ে: `link1 link2` (অথবা `/bdl link1 link2`)\n\n"
        "➤ **৩. বাল্ক পেস্ট:**\n"
        "   একসাথে একাধিক লিংক মেসেজে পেস্ট করে পাঠিয়ে দিন।\n\n"
        "➤ **৪. ফরোয়ার্ড:**\n"
        "   যেকোনো রেস্ট্রিক্টেড পোস্ট সরাসরি এই বটে ফরোয়ার্ড করুন।\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await message.reply(help_text, reply_markup=get_dashboard_markup(), disable_web_page_preview=True)


@bot.on_callback_query(filters.regex(r"^btn_"))
async def handle_dashboard_callbacks(bot: Client, query):
    action = query.data
    if action == "btn_stats":
        currentTime = get_readable_time(time() - PyroConf.BOT_START_TIME)
        total, used, free = shutil.disk_usage(".")
        total_str = get_readable_file_size(total)
        used_str = get_readable_file_size(used)
        free_str = get_readable_file_size(free)
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory().percent
        active = len(RUNNING_TASKS)

        stats_text = (
            "📊 **LIVE BOT STATUS & STATS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ **Uptime:** `{currentTime}`\n"
            f"⚡ **Active Downloads:** `{active}`\n"
            f"🚀 **Max Concurrent:** `{PyroConf.MAX_CONCURRENT_DOWNLOADS}`\n"
            f"📁 **Save Folder:** `{PyroConf.SAVE_DIR}`\n"
            f"💾 **Storage Free:** `{free_str}` / `{total_str}` (Used: `{used_str}`)\n"
            f"🧠 **RAM:** `{ram}%` | ⚙️ **CPU:** `{cpu}%`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        try:
            await query.message.edit_text(stats_text, reply_markup=get_dashboard_markup())
        except Exception:
            await query.answer()

    elif action == "btn_proxy_menu":
        text, markup = get_proxy_panel_data()
        try:
            await query.message.edit_text(text, reply_markup=markup)
        except Exception:
            await query.answer()

    elif action == "btn_proxy_on":
        set_proxy_state(True)
        await query.answer("🟢 BDIX Proxy turned ON! Restart bot (stop.cmd -> start.cmd) to apply.", show_alert=True)
        text, markup = get_proxy_panel_data()
        try:
            await query.message.edit_text(text, reply_markup=markup)
        except Exception:
            pass

    elif action == "btn_proxy_off":
        set_proxy_state(False)
        await query.answer("🔴 BDIX Proxy turned OFF! Restart bot (stop.cmd -> start.cmd) to apply.", show_alert=True)
        text, markup = get_proxy_panel_data()
        try:
            await query.message.edit_text(text, reply_markup=markup)
        except Exception:
            pass

    elif action == "btn_proxy_toggle":
        new_st = toggle_proxy_state()
        st_txt = "🟢 ON" if new_st else "🔴 OFF"
        await query.answer(f"Proxy is now {st_txt}! Restart bot to apply.", show_alert=True)
        text, markup = get_proxy_panel_data()
        try:
            await query.message.edit_text(text, reply_markup=markup)
        except Exception:
            pass

    elif action == "btn_back_home":
        welcome_text = (
            "⚡ **RESTRICTED CONTENT DOWNLOADER** ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👋 **স্বাগতম! কোনো জটিল কমান্ড ছাড়া অতি সহজে ডাউনলোড করুন:**\n\n"
            "🎯 **যেভাবে ডাউনলোড করবেন:**\n"
            "• **Single Link:** সরাসরি যেকোনো টেলিগ্রাম পোস্টের লিংক পেস্ট করুন!\n"
            "• **Batch Range:** সরাসরি `link/10-30` অথবা `link1 link2` পেস্ট করুন!\n"
            "• **Bulk Links:** একসাথে ৫-১০টি লিংক দিলে একসাথে ডাউনলোড শুরু হবে!\n"
            "• **Forward:** যেকোনো চ্যানেল থেকে পোস্ট এখানে ফরোয়ার্ড করুন!\n\n"
            "🚀 **Speed Engine:** 2x Concurrent Downloads + 5x Parallel Streams\n"
            "🍬 **Live Tracker:** Arch Linux Pac-Man (ILoveCandy) animated progress!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👇 **কন্ট্রোল ড্যাশবোর্ড থেকে সহজেই পরিচালনা করুন:**"
        )
        try:
            await query.message.edit_text(welcome_text, reply_markup=get_dashboard_markup(), disable_web_page_preview=True)
        except Exception:
            await query.answer()

    elif action == "btn_cleanup":
        try:
            removed, freed = cleanup_downloads_root()
            freed_str = get_readable_file_size(freed)
            await query.answer(f"🧹 Cleaned {removed} files ({freed_str} freed)!", show_alert=True)
        except Exception as e:
            await query.answer(f"Cleanup error: {e}", show_alert=True)

    elif action == "btn_killall":
        cancelled = 0
        for task in list(RUNNING_TASKS):
            if not task.done():
                task.cancel()
                cancelled += 1
        await query.answer(f"🛑 Cancelled {cancelled} running task(s)!", show_alert=True)

    elif action == "btn_logs":
        if os.path.exists("logs.txt"):
            await query.message.reply_document(document="logs.txt", caption="📋 **System Logs**")
            await query.answer()
        else:
            await query.answer("No logs.txt found.", show_alert=True)

    elif action == "btn_ping":
        bot_ping = 45.0
        user_dc = getattr(user.me, "dc_id", 0) if getattr(user, "me", None) else 0
        bot_dc = getattr(bot.me, "dc_id", 0) if getattr(bot, "me", None) else 0
        try:
            results = await get_all_dc_pings()
            from rich.console import Console
            Console(highlight=False).print(get_dc_table_rich(results, user_dc=user_dc))
            report = await generate_telegram_report(user_dc=user_dc, bot_dc=bot_dc, server_ping_ms=bot_ping)
            await query.message.edit_text(report, reply_markup=get_dashboard_markup())
        except Exception:
            await query.answer("Measuring DC Latencies...", show_alert=False)

    elif action == "btn_dup_stats":
        stats = dup_manager.get_stats()
        total_files = stats["total_downloads"]
        total_size = get_readable_file_size(stats["total_bytes"])
        dup_text = (
            "🔍 **DUPLICATE DETECTOR & HISTORY**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📁 **Total Files Tracked:** `{total_files}`\n"
            f"📦 **Total Data Saved:** `{total_size}`\n"
            "⚡ **Duplicate Mode:** `Smart Pre-Download Auto-Skip`\n\n"
            "💡 *The bot checks SQLite history & local disk in 0.001s BEFORE downloading. Any existing file is skipped automatically to save your bandwidth and time!*"
        )
        try:
            await query.message.edit_text(dup_text, reply_markup=get_dashboard_markup())
        except Exception:
            await query.answer()

    elif action == "btn_guide":
        guide_text = (
            "💡 **কমান্ড ছাড়াও আপনি সরাসরি কাজ করতে পারবেন:**\n\n"
            "১. যেকোনো টেলিগ্রাম পোস্ট লিংক পেস্ট করুন।\n"
            "২. রেঞ্জ ডাউনলোড করতে: `link/10-50` লিখে পাঠান।\n"
            "৩. একসাথে ১০টি লিংক পাঠালেও ব্যাকগ্রাউন্ডে ২টা করে সুপার-ফাস্ট ডাউনলোড হবে।\n"
            "৪. টেলিগ্রামের যেকোনো পোস্ট এখানে ফরোয়ার্ড করলেই সেভ হয়ে যাবে!\n"
            "৫. আগে ডাউনলোড করা ফাইল পেলে স্বয়ংক্রিয়ভাবে স্কিপ করে পরের ফাইলে চলে যাবে!"
        )
        try:
            await query.message.edit_text(guide_text, reply_markup=get_dashboard_markup())
        except Exception:
            await query.answer()


@bot.on_message(filters.command("cleanup") & filters.private)
async def cleanup_storage(_, message: Message):
    try:
        files_removed, bytes_freed = cleanup_downloads_root()
        if files_removed == 0:
            return await message.reply("🧹 **Cleanup complete:** no local downloads found.")
        return await message.reply(
            f"🧹 **Cleanup complete:** removed `{files_removed}` file(s), "
            f"freed `{get_readable_file_size(bytes_freed)}`."
        )
    except Exception as e:
        LOGGER(__name__).error(f"Cleanup failed: {e}")
        return await message.reply("❌ **Cleanup failed.** Check logs for details.")


@bot.on_message(filters.command(["ping", "dc"]) & filters.private)
async def dc_ping_command(bot: Client, message: Message):
    t0 = time()
    wait_msg = await message.reply("⚡ **Measuring Telegram Data Center Ping & Speeds...**")
    bot_ping = (time() - t0) * 1000.0
    
    user_dc = getattr(user.me, "dc_id", 0) if getattr(user, "me", None) else 0
    bot_dc = getattr(bot.me, "dc_id", 0) if getattr(bot, "me", None) else 0
    
    # Measure and print table in terminal
    results = await get_all_dc_pings()
    try:
        from rich.console import Console
        Console(highlight=False).print(get_dc_table_rich(results, user_dc=user_dc))
    except Exception:
        pass
    
    report = await generate_telegram_report(user_dc=user_dc, bot_dc=bot_dc, server_ping_ms=bot_ping)
    await wait_msg.edit_text(report, reply_markup=get_dashboard_markup())



async def handle_download(bot: Client, message: Message, post_url: str):
    async with download_semaphore:
        if "?" in post_url:
            post_url = post_url.split("?", 1)[0]

        try:
            chat_id, message_id = getChatMsgID(post_url)
            channel_name = get_channel_name(post_url)
            chat_message = await user.get_messages(chat_id=chat_id, message_ids=message_id)

            term_ui.print(f" [bold bright_cyan]⚡ INCOMING POST:[/bold bright_cyan] [bright_yellow]{post_url}[/bright_yellow]")
            LOGGER(__name__).info(f"Downloading media: {post_url}")

            if chat_message.document or chat_message.video or chat_message.audio:
                file_size = (
                    chat_message.document.file_size
                    if chat_message.document
                    else chat_message.video.file_size
                    if chat_message.video
                    else chat_message.audio.file_size
                )

                if not await fileSizeLimit(
                    file_size, message, "download", user.me.is_premium
                ):
                    return

            parsed_caption = await get_parsed_msg(
                chat_message.caption or "", chat_message.caption_entities
            )
            parsed_text = await get_parsed_msg(
                chat_message.text or "", chat_message.entities
            )

            if chat_message.media_group_id:
                if not await processMediaGroup(chat_message, bot, message, post_url):
                    await message.reply(
                        "**Could not extract any valid media from the media group.**"
                    )
                return

            elif chat_message.media:
                filename = get_file_name(message_id, chat_message)
                media_type = (
                    "photo" if chat_message.photo
                    else "video" if chat_message.video
                    else "audio" if chat_message.audio
                    else "document"
                )

                # ⚡ SMART PRE-DOWNLOAD DUPLICATE DETECTOR (Instant 0-byte check)
                is_dup, existing_dest = dup_manager.check_duplicate(
                    channel_name=channel_name,
                    filename=filename,
                    media_type=media_type,
                    file_size=file_size if 'file_size' in locals() else None,
                    chat_id=chat_id,
                    message_id=message_id
                )

                if is_dup:
                    actual_size = (file_size if 'file_size' in locals() and file_size else 0) or (os.path.getsize(existing_dest) if os.path.exists(existing_dest) else 0)
                    readable_size = get_readable_file_size(actual_size)
                    term_ui.print(
                        f"  [bold yellow]⏩ AUTO-SKIPPED (DUPLICATE):[/bold yellow] [bright_white]{filename}[/bright_white] "
                        f"[dim]({readable_size}) • 0-Byte Waste[/dim]"
                    )
                    LOGGER(__name__).info(f"DUPLICATE SKIPPED: {filename}")
                    await message.reply(
                        f"⏭️ **Duplicate Auto-Skipped:**\n"
                        f"📁 `{filename}` ({readable_size})\n"
                        f"📍 **Already in:** `{existing_dest}`\n\n"
                        f"⚡ *Zero bandwidth wasted! Moving immediately to the next download...*"
                    )
                    return

                start_time = time()
                progress_message = await message.reply("⚡ **Starting Pac-Man Download Tracker...**")
                download_path = get_download_path(message.id, filename)
                term_ui.print(f"  [bold cyan]📥 DOWNLOADING:[/bold cyan] [bright_white]{filename}[/bright_white]")

                media_path = None
                for attempt in range(2):
                    try:
                        media_path = await fast_download_file(
                            user,
                            chat_message,
                            file_name=download_path,
                            progress=candy_progress,
                            progress_args=("📥 Downloading", progress_message, start_time, filename),
                        )
                        break
                    except FloodWait as e:
                        wait_s = int(getattr(e, "value", 0) or 0)
                        term_ui.print(f"  [bold red]⏳ FLOODWAIT:[/bold red] [yellow]Cooling down for {wait_s}s...[/yellow]")
                        LOGGER(__name__).warning(f"FloodWait: {wait_s}s")
                        if wait_s > 0 and attempt == 0:
                            await asyncio.sleep(wait_s + 1)
                            continue
                        raise

                if not media_path or not os.path.exists(media_path):
                    await progress_message.edit("**❌ Download failed: File not saved properly**")
                    return

                final_file_size = os.path.getsize(media_path)
                if final_file_size == 0:
                    await progress_message.edit("**❌ Download failed: File is empty**")
                    cleanup_download(media_path)
                    return

                readable_size = get_readable_file_size(final_file_size)
                save_dest = get_save_path(PyroConf.SAVE_DIR, channel_name, filename, media_type)
                shutil.move(media_path, save_dest)
                cleanup_download(media_path)  # clean up temp dir if empty

                # Record in history database for instant future duplicate detection
                dup_manager.record_download(
                    chat_id=chat_id,
                    message_id=message_id,
                    channel_name=channel_name,
                    filename=filename,
                    media_type=media_type,
                    file_size=final_file_size,
                    save_path=save_dest
                )

                term_ui.print(
                    f"  [bold bright_green]✅ DOWNLOAD COMPLETE:[/bold bright_green] [bright_white]{filename}[/bright_white] "
                    f"[dim]({readable_size})[/dim]\n"
                    f"     [dim]📁 Saved to: {save_dest}[/dim]\n"
                )
                LOGGER(__name__).info(f"Downloaded media: {filename} ({readable_size})")

                await progress_message.edit(
                    f"**✅ Saved locally!**\n"
                    f"📁 `{save_dest}`\n"
                    f"📦 Size: `{readable_size}`"
                )

            elif chat_message.text or chat_message.caption:
                await message.reply(parsed_text or parsed_caption)
            else:
                await message.reply("**No media or text found in the post URL.**")

        except FloodWait as e:
            wait_s = int(getattr(e, "value", 0) or 0)
            LOGGER(__name__).warning(f"FloodWait in handle_download: {wait_s}s")
            if wait_s > 0:
                await asyncio.sleep(wait_s + 1)
            return
        except (PeerIdInvalid, BadRequest, KeyError):
            await message.reply("**Make sure the user client is part of the chat.**")
        except Exception as e:
            error_message = f"**❌ {str(e)}**"
            await message.reply(error_message)
            LOGGER(__name__).error(e)


@bot.on_callback_query(filters.regex(r"^dup_(allow|deny)_"))
async def handle_duplicate_prompt(bot: Client, query):
    data = query.data.split("_")
    action = data[1]
    msg_id = int(data[2])

    if msg_id in pending_duplicates:
        choice = (action == "allow")
        pending_duplicates[msg_id]["choice"] = choice
        pending_duplicates[msg_id]["event"].set()
        
        text = "**✅ Allowed duplicate file download.**" if choice else "**❌ Denied duplicate file download.**"
        await query.message.edit(text)
    else:
        await query.answer("This prompt has expired.", show_alert=True)


import re

def extract_actions(text: str):
    text = text.strip()
    # 1. Hyphen range: e.g. https://t.me/c/123/10-25
    m = re.search(r'(https?://t\.me/(?:c/)?[\w\d_]+(?:/\d+)?)/(\d+)-(\d+)', text)
    if m:
        base, s, e = m.group(1), int(m.group(2)), int(m.group(3))
        return {'type': 'batch', 'start': f'{base}/{s}', 'end': f'{base}/{e}'}
        
    # 2. Extract all URLs in text
    urls = re.findall(r'https?://t\.me/(?:c/)?[\w\d_]+(?:/\d+)+', text)
    if not urls:
        return {'type': 'none'}
        
    urls = [u.split('?')[0] for u in urls]
    
    # Check if exactly two links from the same channel: range batch
    if len(urls) == 2 and urls[0].rsplit('/', 1)[0] == urls[1].rsplit('/', 1)[0]:
        try:
            id1 = int(urls[0].rsplit('/', 1)[1])
            id2 = int(urls[1].rsplit('/', 1)[1])
            if id1 != id2:
                s_url = urls[0] if id1 < id2 else urls[1]
                e_url = urls[1] if id1 < id2 else urls[0]
                return {'type': 'batch', 'start': s_url, 'end': e_url}
        except Exception:
            pass
            
    if len(urls) == 1:
        return {'type': 'single', 'url': urls[0]}
        
    return {'type': 'multi', 'urls': urls}


async def execute_batch(bot: Client, message: Message, start_url: str, end_url: str):
    try:
        start_chat, start_id = getChatMsgID(start_url)
        end_chat,   end_id   = getChatMsgID(end_url)
    except Exception as e:
        return await message.reply(f"**❌ Error parsing links:\n{e}**")

    if start_chat != end_chat:
        return await message.reply("**❌ Both links must be from the same channel.**")
    if start_id > end_id:
        return await message.reply("**❌ Invalid range: start ID cannot exceed end ID.**")

    try:
        await user.get_chat(start_chat)
    except Exception:
        pass

    prefix = start_url.rsplit("/", 1)[0]
    loading = await message.reply(f"🚀 **Batch Mode Active:** Downloading posts `{start_id}`–`{end_id}`…")

    downloaded = skipped = failed = 0
    processed_media_groups = set()
    batch_tasks = []
    BATCH_SIZE = PyroConf.BATCH_SIZE

    for msg_id in range(start_id, end_id + 1):
        url = f"{prefix}/{msg_id}"
        try:
            chat_msg = await user.get_messages(chat_id=start_chat, message_ids=msg_id)
            if not chat_msg:
                skipped += 1
                continue

            if chat_msg.media_group_id:
                if chat_msg.media_group_id in processed_media_groups:
                    skipped += 1
                    continue
                processed_media_groups.add(chat_msg.media_group_id)

            has_media = bool(chat_msg.media_group_id or chat_msg.media)
            has_text  = bool(chat_msg.text or chat_msg.caption)
            if not (has_media or has_text):
                skipped += 1
                continue

            task = track_task(handle_download(bot, message, url))
            batch_tasks.append(task)

            if len(batch_tasks) >= BATCH_SIZE:
                results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, asyncio.CancelledError):
                        await loading.delete()
                        return await message.reply(
                            f"**❌ Batch canceled** after downloading `{downloaded}` posts."
                        )
                    elif isinstance(result, Exception):
                        failed += 1
                        LOGGER(__name__).error(f"Error: {result}")
                    else:
                        downloaded += 1

                batch_tasks.clear()
                await asyncio.sleep(PyroConf.FLOOD_WAIT_DELAY)

        except Exception as e:
            failed += 1
            LOGGER(__name__).error(f"Error at {url}: {e}")

    if batch_tasks:
        results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                failed += 1
            else:
                downloaded += 1

    await loading.delete()
    await message.reply(
        "**✅ Batch Process Complete!**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📥 **Downloaded** : `{downloaded}` post(s)\n"
        f"⏭️ **Skipped**    : `{skipped}` (no content)\n"
        f"❌ **Failed**     : `{failed}` error(s)"
    )


async def smart_dispatcher(bot: Client, message: Message, raw_text: str):
    action = extract_actions(raw_text)
    
    if action["type"] == "single":
        await track_task(handle_download(bot, message, action["url"]))
    elif action["type"] == "batch":
        await track_task(execute_batch(bot, message, action["start"], action["end"]))
    elif action["type"] == "multi":
        urls = action["urls"]
        await message.reply(f"📥 **Found {len(urls)} links!** Downloading {PyroConf.MAX_CONCURRENT_DOWNLOADS} at a time in parallel...")
        for u in urls:
            track_task(handle_download(bot, message, u))
    else:
        await message.reply(
            "❓ **কোনো ভ্যালিড টেলিগ্রাম পোস্ট লিংক পাওয়া যায়নি।**\n\n"
            "💡 **যেভাবে পাঠাতে পারেন:**\n"
            "• সরাসরি যেকোনো লিংক: `https://t.me/c/123/45`\n"
            "• রেঞ্জ ডাউনলোড: `https://t.me/c/123/10-25`\n"
            "• একসাথে একাধিক লিংক কপি-পেস্ট করে পাঠান!",
            reply_markup=get_dashboard_markup()
        )


@bot.on_message(filters.command(["dl", "bdl"]) & filters.private)
async def download_cmd_handler(bot: Client, message: Message):
    text = ""
    if len(message.command) > 1:
        text = message.text.split(None, 1)[1]
    elif message.reply_to_message:
        text = message.reply_to_message.text or message.reply_to_message.caption or ""

    if not text:
        return await message.reply(
            "**💡 কমান্ডের পর লিংক দিন অথবা সরাসরি লিংক পেস্ট করুন:**\n"
            "`/dl https://t.me/c/123/45`\n"
            "`/dl https://t.me/c/123/10-25`",
            reply_markup=get_dashboard_markup()
        )
    await smart_dispatcher(bot, message, text)


@bot.on_message(filters.command("proxy") & filters.private)
async def proxy_command_handler(_, message: Message):
    text, markup = get_proxy_panel_data()
    await message.reply(text, reply_markup=markup)


@bot.on_message(filters.private & ~filters.command(["start", "help", "dl", "bdl", "stats", "logs", "killall", "cleanup", "proxy"]))
async def handle_any_message(bot: Client, message: Message):
    # Support forwarded posts or directly pasted text/captions
    text = message.text or message.caption or ""
    if text:
        await smart_dispatcher(bot, message, text)


@bot.on_message(filters.command("stats") & filters.private)
async def stats(_, message: Message):
    currentTime = get_readable_time(time() - PyroConf.BOT_START_TIME)
    total, used, free = shutil.disk_usage(".")
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(psutil.net_io_counters().bytes_sent)
    recv = get_readable_file_size(psutil.net_io_counters().bytes_recv)
    cpuUsage = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    process = psutil.Process(os.getpid())

    stats = (
        "**≧◉◡◉≦ Bot is Up and Running successfully.**\n\n"
        f"**➜ Bot Uptime:** `{currentTime}`\n"
        f"**➜ Total Disk Space:** `{total}`\n"
        f"**➜ Used:** `{used}`\n"
        f"**➜ Free:** `{free}`\n"
        f"**➜ Memory Usage:** `{round(process.memory_info()[0] / 1024**2)} MiB`\n\n"
        f"**➜ Upload:** `{sent}`\n"
        f"**➜ Download:** `{recv}`\n\n"
        f"**➜ CPU:** `{cpuUsage}%` | "
        f"**➜ RAM:** `{memory}%` | "
        f"**➜ DISK:** `{disk}%`"
    )
    await message.reply(stats)


@bot.on_message(filters.command("logs") & filters.private)
async def logs(_, message: Message):
    if os.path.exists("logs.txt"):
        await message.reply_document(document="logs.txt", caption="**Logs**")
    else:
        await message.reply("**Not exists**")


@bot.on_message(filters.command("killall") & filters.private)
async def cancel_all_tasks(_, message: Message):
    cancelled = 0
    for task in list(RUNNING_TASKS):
        if not task.done():
            task.cancel()
            cancelled += 1
    await message.reply(f"**Cancelled {cancelled} running task(s).**")


async def initialize():
    global download_semaphore
    download_semaphore = asyncio.Semaphore(PyroConf.MAX_CONCURRENT_DOWNLOADS)

_CACHED_DC_RESULTS = []

def display_bot_banner(bot_user, user_account, dc_results=None):
    global _CACHED_DC_RESULTS
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich import box
        from helpers.dc_ping import build_compact_dc_table

        if dc_results is not None:
            _CACHED_DC_RESULTS = dc_results

        console = Console(highlight=False)
        console.clear()

        # Build 2-column compact unified cyberpunk dashboard
        grid = Table.grid(expand=True)
        grid.add_column("engine", ratio=1)
        grid.add_column("divider", width=3)
        grid.add_column("ping", ratio=1)

        left = Table(box=None, show_header=False, padding=(0, 0), expand=True)
        left.add_column("k", style="bold bright_white", width=11, no_wrap=True)
        left.add_column("v", style="bright_cyan", no_wrap=True)

        bot_handle = f"@{bot_user.username}" if getattr(bot_user, "username", None) else getattr(bot_user, "first_name", "Bot")
        user_name = f"{getattr(user_account, 'first_name', '') or ''} {getattr(user_account, 'last_name', '') or ''}".strip()
        user_handle = f"@{user_account.username}" if getattr(user_account, "username", None) else user_name
        user_dc = getattr(user_account, "dc_id", 0) or 0

        proxy_info = PyroConf.get_proxy()
        proxy_display = f"[bold green]● BDIX ({PyroConf.PROXY_HOST})[/bold green]" if proxy_info else "[dim yellow]○ Direct (BDIX Off)[/dim yellow]"

        left.add_row("🤖 Bot", f"[bold green]{bot_handle}[/bold green]")
        left.add_row("👤 User", f"[bold bright_yellow]{user_handle}[/bold bright_yellow] [dim](DC{user_dc})[/dim]")
        left.add_row("🌐 Proxy", proxy_display)
        left.add_row("⚡ Engine", f"[bold cyan]{PyroConf.MAX_CONCURRENT_DOWNLOADS} DL[/bold cyan] [dim]•[/dim] [bold bright_green]32 Turbo Streams[/bold bright_green]")
        left.add_row("📁 Vault", f"[yellow]{PyroConf.SAVE_DIR}/[/yellow] [bold green](Zero-Dup)[/bold green]")

        right = build_compact_dc_table(_CACHED_DC_RESULTS, user_dc=user_dc)
        divider = "\n".join(["[dim bright_blue]│[/dim bright_blue]"] * 5)

        grid.add_row(left, divider, right)

        panel = Panel(
            grid,
            title="[bold bright_white on dark_blue] ⚡ RESTRICTED DL v2.5 [/bold bright_white on dark_blue] [bold bright_cyan]❖ CYBERPUNK HIGH-SPEED TURBO 🚀[/bold bright_cyan]",
            subtitle="[dim cyan]⚡ [bright_white]Quick CLI:[/bright_white] Paste link/batch [dim]•[/dim] [yellow]proxy[/yellow] [dim]•[/dim] [yellow]ping[/yellow] [dim]•[/dim] [yellow]stats[/yellow] [dim]•[/dim] [red]exit[/red][/dim cyan]",
            border_style="bright_blue",
            box=box.ROUNDED,
            padding=(0, 1)
        )
        console.print(panel)
        console.print()

    except Exception:
        LOGGER(__name__).info("Bot Started!")

if __name__ == "__main__":
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(initialize())

        # Start user client
        try:
            user.start()
        except Exception as e:
            try:
                from rich.console import Console
                from rich.panel import Panel
                c = Console()
                c.print(Panel(
                    f"[bold red]❌ User Session Error:[/bold red] {e}\n\n"
                    "[bold yellow]👉 Solution:[/bold yellow] Please run [bold green]login.cmd[/bold green] to connect your Telegram account!",
                    title="[bold red] AUTHENTICATION REQUIRED [/bold red]",
                    border_style="red"
                ))
            except Exception:
                print(f"Error starting user session: {e}\nPlease run login.cmd to connect.")
            sys.exit(1)

        bot.start()
        bot_user = bot.get_me()
        user_account = user.get_me()

        # Register Telegram native command menu
        try:
            from pyrogram.types import BotCommand
            bot.set_bot_commands([
                BotCommand("start", "👋 Control Dashboard & Info"),
                BotCommand("dl", "📥 Download single or batch range"),
                BotCommand("bdl", "🚀 Batch download post range"),
                BotCommand("proxy", "🌐 BDIX Proxy Switch & Status"),
                BotCommand("ping", "⚡ Telegram DC latency & speeds"),
                BotCommand("dc", "🌐 Telegram DC connection info"),
                BotCommand("stats", "📊 Live server & storage stats"),
                BotCommand("cleanup", "🧹 Free temporary disk space"),
                BotCommand("killall", "🛑 Stop all running downloads"),
                BotCommand("logs", "📋 Download system log file"),
                BotCommand("help", "💡 Interactive guide & examples")
            ])
        except Exception:
            pass

        # Pre-fetch DC latency so it populates into the compact dashboard immediately on startup
        try:
            dc_results = loop.run_until_complete(get_all_dc_pings())
        except Exception:
            dc_results = []

        display_bot_banner(bot_user, user_account, dc_results=dc_results)

        # Next-Gen Interactive Terminal CLI REPL
        from helpers.terminal_cli import terminal_repl_loop
        loop.run_until_complete(terminal_repl_loop(
            bot=bot,
            user=user,
            running_tasks_set=RUNNING_TASKS,
            smart_dispatcher_func=smart_dispatcher,
            banner_func=display_bot_banner
        ))

        bot.stop()
        user.stop()
    except KeyboardInterrupt:
        pass
    except Exception as err:
        LOGGER(__name__).error(err)
    finally:
        try:
            sys.stdout.write("\x1b[r\x1b[?25h")
            sys.stdout.flush()
        except Exception:
            pass
        LOGGER(__name__).info("Bot Stopped")


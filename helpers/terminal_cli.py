import os
import sys
import time
import shutil
import asyncio
import psutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich import box
from logger import LOGGER

from helpers.files import cleanup_downloads_root, get_readable_file_size, get_readable_time
from helpers.dc_ping import get_all_dc_pings, get_dc_table_rich
from helpers.duplicate import dup_manager
from config import PyroConf, set_proxy_state, toggle_proxy_state

console = Console(highlight=False)

class TerminalMessageWrapper:
    """Simulates a Telegram message object so terminal commands can use all bot download logic."""
    def __init__(self, bot, target_user_id: int):
        self.bot = bot
        self.target_user_id = target_user_id
        self.id = int(time.time() * 1000) % 10000000
        self.text = ""
        self.caption = ""
        self.command = []
        self.reply_to_message = None

    async def reply(self, text: str, reply_markup=None, **kwargs):
        # Print notification in terminal
        clean_first_line = text.replace("**", "").replace("`", "").splitlines()[0] if text else ""
        console.print(f" [bold cyan]🤖 Bot:[/bold cyan] [bright_white]{clean_first_line}[/bright_white]")
        
        # Send update to Telegram so user gets mobile notification as well
        if self.target_user_id and self.bot:
            try:
                return await self.bot.send_message(self.target_user_id, text, reply_markup=reply_markup)
            except Exception:
                pass
        
        class LocalDummyMsg:
            def __init__(self, mid):
                self.id = mid
            async def edit(self, *a, **k): pass
            async def edit_text(self, *a, **k): pass
            async def delete(self): pass
        return LocalDummyMsg(self.id)


def print_cli_help():
    table = Table(
        title="[bold bright_yellow]⚡ TERMINAL COMMAND CENTER — QUICK GUIDE ⚡[/bold bright_yellow]",
        box=box.ROUNDED,
        border_style="bright_blue",
        show_header=True,
        header_style="bold bright_white"
    )
    table.add_column("Command / Input", style="bold cyan", width=26)
    table.add_column("Action / Description", style="bright_white")

    table.add_row("<telegram_url>", "Instantly download single post (photo/video/doc)")
    table.add_row("<url>/10-30", "Batch download range from post 10 to 30")
    table.add_row("<url1> <url2>", "Batch download range between two links")
    table.add_row("proxy [on|off|toggle]", "Check or turn BDIX proxy ON / OFF anytime")
    table.add_row("ping or dc", "Test live latency to all 5 Telegram Data Centers")
    table.add_row("stats", "Display live RAM, CPU, Uptime & Active tasks")
    table.add_row("dup", "View Duplicate Detector stats & data saved")
    table.add_row("cleanup", "Purge temporary download files to free disk space")
    table.add_row("killall", "Cancel all running download tasks immediately")
    table.add_row("clear", "Clear terminal screen and re-display main dashboard")
    table.add_row("exit or quit", "Cleanly stop and shut down the bot")
    console.print(table)
    console.print()


async def terminal_repl_loop(bot, user, running_tasks_set, smart_dispatcher_func, banner_func=None):
    """Next-level interactive CLI running concurrently with the bot engine."""
    loop = asyncio.get_running_loop()
    user_id = getattr(user.me, "id", None) if getattr(user, "me", None) else None
    user_dc = getattr(user.me, "dc_id", 0) if getattr(user, "me", None) else 0

    console.print(" [bold bright_green]💡 Interactive Terminal CLI Ready[/bold bright_green] [dim]• Paste any link below or type [yellow]help[/yellow][/dim]\n")

    while True:
        try:
            # Non-blocking async prompt input with cyber styling
            prompt_str = "\x1b[1;36m⚡ [RestrictedDL]\x1b[0m \x1b[1;32m❯\x1b[0m "
            raw_input = await loop.run_in_executor(None, input, prompt_str)
            cmd = raw_input.strip()

            if not cmd:
                continue

            low_cmd = cmd.lower()

            if low_cmd in ["exit", "quit", "q"]:
                console.print("\n[bold red]🛑 Stopping Bot from Terminal...[/bold red]")
                break

            elif low_cmd in ["help", "?"]:
                print_cli_help()

            elif low_cmd in ["proxy", "bdix"]:
                is_on = PyroConf.USE_PROXY and bool(PyroConf.get_proxy())
                status_txt = "[bold green]● Active (ON)[/bold green]" if is_on else "[bold yellow]○ Inactive (OFF)[/bold yellow]"
                p_table = Table(box=None, show_header=False, expand=True)
                p_table.add_column("Key", style="bold bright_white", width=18)
                p_table.add_column("Value", style="bright_cyan")
                p_table.add_row("🌐 Status", status_txt)
                p_table.add_row("⚡ Host", f"[yellow]{PyroConf.PROXY_HOST or 'None'}[/yellow]")
                p_table.add_row("🔌 Port", f"[yellow]{PyroConf.PROXY_PORT}[/yellow]")
                p_table.add_row("🛡️ Protocol", f"[magenta]{PyroConf.PROXY_SCHEME.upper()} (BDIX Squid)[/magenta]")
                p_table.add_row("👤 User", f"[cyan]{PyroConf.PROXY_USER or 'None'}[/cyan]")
                p_table.add_row("💡 Quick Toggle", "[bright_white]Type [green]proxy on[/green], [yellow]proxy off[/yellow], or [cyan]proxy toggle[/cyan][/bright_white]")

                console.print(Panel(p_table, title="[bold bright_cyan] 🌐 BDIX PROXY CONTROLLER [/bold bright_cyan]", border_style="cyan", box=box.ROUNDED))
                console.print()

            elif low_cmd in ["proxy on", "bdix on"]:
                set_proxy_state(True)
                console.print("[bold green]✔ BDIX Proxy is now ENABLED in config.env![/bold green]")
                console.print("[dim]👉 Please restart the bot (stop.cmd then start.cmd) to apply to active Telegram sessions.\n[/dim]")
                if banner_func and bot.me and user.me:
                    try:
                        banner_func(bot.me, user.me)
                    except Exception:
                        pass

            elif low_cmd in ["proxy off", "bdix off"]:
                set_proxy_state(False)
                console.print("[bold yellow]✔ BDIX Proxy is now DISABLED in config.env![/bold yellow]")
                console.print("[dim]👉 Please restart the bot (stop.cmd then start.cmd) to connect directly without proxy.\n[/dim]")
                if banner_func and bot.me and user.me:
                    try:
                        banner_func(bot.me, user.me)
                    except Exception:
                        pass

            elif low_cmd in ["proxy toggle", "bdix toggle"]:
                new_state = toggle_proxy_state()
                if new_state:
                    console.print("[bold green]✔ BDIX Proxy is now ENABLED in config.env![/bold green]")
                else:
                    console.print("[bold yellow]✔ BDIX Proxy is now DISABLED in config.env![/bold yellow]")
                console.print("[dim]👉 Please restart the bot (stop.cmd then start.cmd) to apply changes.\n[/dim]")
                if banner_func and bot.me and user.me:
                    try:
                        banner_func(bot.me, user.me)
                    except Exception:
                        pass

            elif low_cmd in ["ping", "dc"]:
                with console.status("[bold cyan]Pinging Telegram Data Centers (DC1 - DC5)...", spinner="aesthetic"):
                    results = await get_all_dc_pings()
                console.print(get_dc_table_rich(results, user_dc=user_dc))
                console.print()
                if banner_func and bot.me and user.me:
                    try:
                        banner_func(bot.me, user.me, dc_results=results)
                    except TypeError:
                        banner_func(bot.me, user.me)

            elif low_cmd == "stats":
                currentTime = get_readable_time(time.time() - PyroConf.BOT_START_TIME)
                total, used, free = shutil.disk_usage(".")
                cpu = psutil.cpu_percent(interval=0.2)
                ram = psutil.virtual_memory().percent
                active = len(running_tasks_set)

                stat_table = Table(box=None, show_header=False, expand=True)
                stat_table.add_column("Key", style="bold bright_white", width=22)
                stat_table.add_column("Value", style="bright_cyan")

                stat_table.add_row("⏱️  Uptime", f"[yellow]{currentTime}[/yellow]")
                stat_table.add_row("⚡ Active Tasks", f"[bold green]{active}[/bold green]")
                stat_table.add_row("🚀 Max Concurrent", f"[cyan]{PyroConf.MAX_CONCURRENT_DOWNLOADS} Parallel Tasks[/cyan]")
                stat_table.add_row("🧠 RAM Usage", f"[magenta]{ram}%[/magenta]")
                stat_table.add_row("⚙️  CPU Usage", f"[magenta]{cpu}%[/magenta]")
                stat_table.add_row("💾 Disk Free", f"[bold green]{get_readable_file_size(free)}[/bold green] [dim]/ {get_readable_file_size(total)}[/dim]")

                console.print(Panel(stat_table, title="[bold bright_yellow] 📊 SYSTEM TELEMETRY 📊 [/bold bright_yellow]", border_style="bright_blue", box=box.ROUNDED))
                console.print()

            elif low_cmd == "dup":
                stats = dup_manager.get_stats()
                console.print(Panel(
                    f"📁 [bold cyan]Total Files Tracked:[/bold cyan] [bold green]{stats['total_downloads']}[/bold green]\n"
                    f"📦 [bold cyan]Total Data Saved:[/bold cyan] [bold yellow]{get_readable_file_size(stats['total_bytes'])}[/bold yellow]\n"
                    f"⚡ [bold cyan]Mode:[/bold cyan] [bold green]Zero-Byte Pre-Download Auto-Skip[/bold green]",
                    title="[bold bright_green] 🔍 DUPLICATE DETECTOR TELEMETRY [/bold bright_green]",
                    border_style="green"
                ))
                console.print()

            elif low_cmd == "cleanup":
                removed, freed = cleanup_downloads_root()
                console.print(f"[bold green]🧹 Cleanup complete:[/bold green] Removed {removed} temporary files ([yellow]{get_readable_file_size(freed)}[/yellow] freed)!\n")

            elif low_cmd == "killall":
                cancelled = 0
                for task in list(running_tasks_set):
                    if not task.done():
                        task.cancel()
                        cancelled += 1
                console.print(f"[bold yellow]🛑 Cancelled {cancelled} running task(s).[/bold yellow]\n")

            elif low_cmd in ["clear", "cls", "c"]:
                console.clear()
                if banner_func and bot.me and user.me:
                    banner_func(bot.me, user.me)

            else:
                # Treat as Telegram link or batch range input
                mock_msg = TerminalMessageWrapper(bot, user_id)
                console.print(f"[bold cyan]📥 Processing input:[/bold cyan] [bright_yellow]{cmd}[/bright_yellow]")
                asyncio.create_task(smart_dispatcher_func(bot, mock_msg, cmd))

        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold red]🛑 Stopping Bot cleanly...[/bold red]")
            break
        except Exception as e:
            console.print(f"[bold red]✖ Terminal CLI Error:[/bold red] {e}\n")

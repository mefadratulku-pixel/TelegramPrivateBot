import os
import re
import sys
import asyncio
import logging

# Ensure full UTF-8 support in Windows terminal
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Suppress verbose Pyrogram & library logs
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.ERROR)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.align import Align
from rich import box
from dotenv import load_dotenv

load_dotenv("config.env.local", interpolate=False, override=True)
load_dotenv("config.env", interpolate=False, override=True)

from pyrogram import Client, errors
from config import PyroConf

console = Console(highlight=False)

API_ID = int(os.getenv("API_ID", "37134777"))
API_HASH = os.getenv("API_HASH", "db05fa7ce130a20867b249c92c9d81e6")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

ASCII_BANNER = r"""
 [bold cyan]██████╗ ███████╗███████╗████████╗██████╗ ██╗ ██████╗████████╗███████╗██████╗ [/bold cyan]
 [bold cyan]██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗██║██╔════╝╚══██╔══╝██╔════╝██╔══██╗[/bold cyan]
 [bold bright_blue]██████╔╝█████╗  ███████╗   ██║   ██████╔╝██║██║        ██║   █████╗  ██║  ██║[/bold bright_blue]
 [bold bright_blue]██╔══██╗██╔══╝  ╚════██║   ██║   ██╔══██╗██║██║        ██║   ██╔══╝  ██║  ██║[/bold bright_blue]
 [bold magenta]██║  ██║███████╗███████║   ██║   ██║  ██║██║╚██████╗   ██║   ███████╗██████╔╝[/bold magenta]
 [bold magenta]╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝ ╚═════╝   ╚═╝   ╚══════╝╚═════╝ [/bold magenta]
          [bold bright_yellow]⚡ TELEGRAM USER SESSION AUTHENTICATOR ⚡[/bold bright_yellow]
"""

def render_header():
    try:
        console.clear()
    except Exception:
        pass
    console.print(Align.center(ASCII_BANNER))
    
    proxy_info = PyroConf.get_proxy()
    proxy_str = f"[bold green]● Active ({PyroConf.PROXY_HOST}:{PyroConf.PROXY_PORT})[/bold green]" if proxy_info else "[dim yellow]○ Inactive (Direct)[/dim yellow]"

    info_table = Table(box=box.ROUNDED, border_style="cyan", show_header=False, expand=True)
    info_table.add_column("Key", style="bold bright_white", width=22)
    info_table.add_column("Value", style="bright_cyan")
    
    info_table.add_row("🤖 Target Bot", "[bold green]@mydloaderbot[/bold green] [dim](mydloader)[/dim]")
    info_table.add_row("🔑 Telegram API ID", f"[yellow]{API_ID}[/yellow]")
    info_table.add_row("🛡️ Auth Engine", "[magenta]Pyrofork v2.3.68[/magenta] [dim](In-Memory Session)[/dim]")
    info_table.add_row("🌐 BDIX Proxy", proxy_str)
    info_table.add_row("⚡ Auth Mode", "[bold green]Interactive Terminal Login[/bold green]")
    
    panel = Panel(
        info_table,
        title="[bold bright_yellow] ✨ SYSTEM CONFIGURATION ✨ [/bold bright_yellow]",
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
        padding=(0, 2)
    )
    console.print(panel)
    console.print()

async def authenticate_account():
    render_header()
    
    app = Client(
        name="session_generator",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
        proxy=PyroConf.get_proxy()
    )
    
    with console.status("[bold cyan]Connecting to Telegram DC servers...", spinner="aesthetic"):
        await app.connect()
    
    console.print("[bold green]✔[/bold green] [bright_white]Connected to Telegram servers safely.[/bright_white]\n")
    
    # 1. Ask for Phone Number
    while True:
        phone_number = Prompt.ask(
            "[bold cyan]📱 Enter your Telegram phone number[/bold cyan] [dim](with country code, e.g. +8801XXXXXXXXX)[/dim]"
        ).strip().replace(" ", "")
        
        if not phone_number.startswith("+"):
            console.print("[bold red]✖ Error:[/bold red] Phone number must start with '+' (e.g. +8801XXXXXXXXX)\n")
            continue
            
        confirm = Confirm.ask(f"[yellow]Is [bold white]{phone_number}[/bold white] correct?[/yellow]", default=True)
        if confirm:
            break

    # 2. Send Code
    sent_code = None
    with console.status(f"[bold yellow]Sending authentication code to {phone_number}...", spinner="dots12"):
        try:
            sent_code = await app.send_code(phone_number)
        except errors.FloodWait as e:
            console.print(f"\n[bold red]✖ FloodWait Error:[/bold red] Telegram requires waiting [yellow]{e.value}[/yellow] seconds.")
            await app.disconnect()
            return
        except Exception as e:
            console.print(f"\n[bold red]✖ Error sending code:[/bold red] {e}")
            await app.disconnect()
            return

    console.print(f"\n[bold green]✔[/bold green] [bold bright_white]Verification code sent via [yellow]{sent_code.type.name}[/yellow]![/bold bright_white]")
    console.print("[dim]Please check your official Telegram app inbox for the confirmation code.[/dim]\n")

    # 3. Enter confirmation code
    signed_in = None
    while True:
        phone_code = Prompt.ask("[bold green]🔑 Enter the confirmation code[/bold green]").strip()
        
        with console.status("[bold cyan]Verifying confirmation code...", spinner="aesthetic"):
            try:
                signed_in = await app.sign_in(phone_number, sent_code.phone_code_hash, phone_code)
                break
            except errors.SessionPasswordNeeded:
                console.print("\n[bold yellow]🔒 Two-Step Verification (2FA) is enabled on this account.[/bold yellow]")
                while True:
                    password = Prompt.ask("[bold magenta]🔐 Enter your 2FA password[/bold magenta]", password=True)
                    with console.status("[bold cyan]Verifying 2FA password...", spinner="aesthetic"):
                        try:
                            signed_in = await app.check_password(password)
                            break
                        except errors.PasswordHashInvalid:
                            console.print("[bold red]✖ Invalid password![/bold red] Please try again.\n")
                break
            except errors.PhoneCodeInvalid:
                console.print("[bold red]✖ Invalid code![/bold red] Please check Telegram and try again.\n")
            except errors.PhoneCodeExpired:
                console.print("[bold red]✖ Code expired![/bold red] Please restart login.cmd to request a fresh code.")
                await app.disconnect()
                return
            except Exception as e:
                console.print(f"\n[bold red]✖ Sign-in failed:[/bold red] {e}")
                await app.disconnect()
                return

    # 4. Export session & fetch profile
    with console.status("[bold cyan]Generating high-security session string...", spinner="bouncingBall"):
        session_string = await app.export_session_string()
        me = await app.get_me()
        await app.disconnect()

    # 5. Save to config.env
    config_path = "config.env"
    with open(config_path, "r", encoding="utf-8") as f:
        config_content = f.read()

    if re.search(r"^SESSION_STRING\s*=.*$", config_content, flags=re.MULTILINE):
        new_config = re.sub(
            r"^SESSION_STRING\s*=.*$",
            f"SESSION_STRING = {session_string}",
            config_content,
            flags=re.MULTILINE
        )
    else:
        new_config = config_content.rstrip() + f"\nSESSION_STRING = {session_string}\n"

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_config)

    # 6. Render Gorgeous Success Card
    console.print("\n")
    success_table = Table(box=box.DOUBLE_EDGE, border_style="bright_green", show_header=False, expand=True)
    success_table.add_column("Attribute", style="bold bright_white", width=22)
    success_table.add_column("Detail", style="bold bright_cyan")

    full_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    username_str = f"@{me.username}" if me.username else "[dim]None[/dim]"
    phone_str = f"+{me.phone_number}" if me.phone_number else "[dim]Hidden[/dim]"

    success_table.add_row("👤 Account Name", f"[bold green]{full_name}[/bold green]")
    success_table.add_row("🏷️ Username", f"[bold bright_yellow]{username_str}[/bold bright_yellow]")
    success_table.add_row("🆔 User ID", f"[cyan]{me.id}[/cyan]")
    success_table.add_row("📞 Phone Number", f"[white]{phone_str}[/white]")
    success_table.add_row("💾 Session Status", "[bold green]Saved to config.env (ACTIVE)[/bold green]")
    success_table.add_row("🚀 Bot Ready", "[bold green]YES — Ready to Download[/bold green]")

    success_panel = Panel(
        success_table,
        title="[bold bright_green] 🎉 ACCOUNT SUCCESSFULLY CONNECTED! 🎉 [/bold bright_green]",
        border_style="bright_green",
        padding=(1, 2)
    )
    console.print(success_panel)

    next_panel = Panel(
        Align.center(
            "[bold bright_white]👉 Step 1: Run [bold bright_yellow]start.cmd[/bold bright_yellow] to launch your bot!\n"
            "👉 Step 2: Open Telegram and message [bold green]@mydloaderbot[/bold green] with your links![/bold bright_white]"
        ),
        title="[bold bright_yellow] 🚀 Next Step [/bold bright_yellow]",
        border_style="yellow",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(next_panel)
    console.print()

if __name__ == "__main__":
    try:
        asyncio.run(authenticate_account())
    except KeyboardInterrupt:
        console.print("\n[bold red][!] Session setup cancelled by user.[/bold red]\n")
    except Exception as e:
        console.print(f"\n[bold red][FATAL ERROR][/bold red] {e}\n")

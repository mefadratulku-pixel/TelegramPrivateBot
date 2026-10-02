@echo off
chcp 65001 >nul
title BDIX Proxy Controller
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "from config import toggle_proxy_state, PyroConf; from rich.console import Console; from rich.panel import Panel; c = Console(); new_st = toggle_proxy_state(); msg = f'[bold green]🚀 BDIX Proxy is now ENABLED (ON)![/bold green]\n\n🌐 [bright_cyan]Server:[/bright_cyan] {PyroConf.PROXY_HOST}:{PyroConf.PROXY_PORT}\n🛡️ [bright_cyan]Protocol:[/bright_cyan] HTTP (BDIX)\n\n[bright_white]👉 Please restart the bot (stop.cmd then start.cmd) to apply.[/bright_white]' if new_st else '[bold yellow]🛑 BDIX Proxy is now DISABLED (OFF)![/bold yellow]\n\n🌐 [bright_cyan]Mode:[/bright_cyan] Direct Internet Connection\n\n[bright_white]👉 Please restart the bot (stop.cmd then start.cmd) to apply.[/bright_white]'; c.print(Panel(msg, title='[bold cyan] 🌐 BDIX PROXY CONTROLLER [/bold cyan]', border_style='bright_cyan'))"
) else (
    python -c "from config import toggle_proxy_state, PyroConf; new_st = toggle_proxy_state(); print('\n===============================\n  BDIX PROXY: ' + ('ENABLED (ON)' if new_st else 'DISABLED (OFF)') + '\n===============================\nRestart bot (stop.cmd -> start.cmd) to apply.\n')"
)

echo.
pause

import time
import math
import asyncio
from rich.console import Console
from logger import LOGGER

console = Console(highlight=False)

def format_bytes(size: float) -> str:
    if not size or size < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"

def format_time(seconds: float) -> str:
    if not seconds or seconds < 0 or math.isinf(seconds):
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def make_candy_bar(percentage: float, total_slots: int = 12) -> str:
    percentage = max(0.0, min(100.0, float(percentage)))
    pos = int((percentage / 100.0) * total_slots)
    pos = max(0, min(total_slots, pos))
    
    # Animated mouth opening/closing based on timestamp
    mouth = "ᗧ" if int(time.time() * 2.5) % 2 == 0 else "ᗤ"
    
    if pos >= total_slots:
        return f"👻 {'━' * total_slots}{mouth} 🍒"
    
    eaten = "━" * pos
    remaining = total_slots - pos - 1
    candies = " •" * remaining if remaining > 0 else ""
    return f"👻 {eaten}{mouth}{candies} 🍒"

def make_rich_candy_bar(percentage: float, total_slots: int = 12) -> str:
    percentage = max(0.0, min(100.0, float(percentage)))
    pos = int((percentage / 100.0) * total_slots)
    pos = max(0, min(total_slots, pos))
    
    # Authentic Arch Linux ILoveCandy Pac-Man: 'C' (open mouth) and 'c' (closed mouth)
    # 100% universal across all Windows fonts without turning into 'D'
    mouth = "C" if int(time.time() * 2.5) % 2 == 0 else "c"
    
    if pos >= total_slots:
        return f"[bold red]👻[/bold red] [dim cyan]{'━' * total_slots}[/dim cyan][bold bright_yellow]{mouth}[/bold bright_yellow] [bold red]🍒[/bold red]"
    
    eaten = f"[dim cyan]{'━' * pos}[/dim cyan]"
    remaining = total_slots - pos - 1
    candies = f"[bold bright_white]{' •' * remaining}[/bold bright_white]" if remaining > 0 else ""
    return f"[bold red]👻[/bold red] {eaten}[bold bright_yellow]{mouth}[/bold bright_yellow]{candies} [bold red]🍒[/bold red]"

_TRACKER_STATES = {}

async def candy_progress(current: int, total: int, action: str, progress_message, start_time: float, file_name: str = ""):
    if not total or total <= 0:
        return
        
    now = time.time()
    msg_id = getattr(progress_message, "id", None) or id(progress_message)
    state = _TRACKER_STATES.setdefault(msg_id, {
        "last_tg": 0.0,
        "last_term": 0.0,
    })
    
    percentage = (current * 100.0) / total
    diff = max(now - start_time, 0.001)
    speed = current / diff
    eta = (total - current) / speed if speed > 0 else 0
    is_finished = (current >= total)
    
    # 1. Terminal In-Place Console Update (updates strictly on the SAME line without newlines)
    if (now - state["last_term"] >= 0.3) or is_finished:
        state["last_term"] = now
        rich_bar = make_rich_candy_bar(percentage, total_slots=8)
        cur_str = format_bytes(current)
        tot_str = format_bytes(total)
        spd_str = f"{format_bytes(speed)}/s"
        eta_str = format_time(eta)
        
        line_output = (
            f" {rich_bar} [bold green]{percentage:5.1f}%[/bold green] │ "
            f"[cyan]{cur_str}/{tot_str}[/cyan] │ "
            f"[bold yellow]⚡ {spd_str:>9}[/bold yellow] │ "
            f"[magenta]⏱ {eta_str}[/magenta]"
        )
        
        # Clear current line and update in-place using carriage return \r
        if is_finished:
            console.print(f"\r\x1b[2K{line_output}\n")
        else:
            console.print(f"\r\x1b[2K{line_output}", end="\r")

    # 2. Telegram Message Edit (every 3.5s or on completion to prevent FloodWait)
    if (now - state["last_tg"] >= 3.5) or is_finished:
        state["last_tg"] = now
        tg_bar = make_candy_bar(percentage, total_slots=12)
        cur_str = format_bytes(current)
        tot_str = format_bytes(total)
        spd_str = f"{format_bytes(speed)}/s"
        eta_str = format_time(eta)
        elapsed_str = format_time(diff)
        
        file_line = f"📁 **File:** `{file_name}`\n" if file_name else ""
        tg_text = (
            f"⚡ **PAC-MAN DOWNLOAD TRACKER** ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"`{tg_bar}` **[{percentage:.1f}%]**\n\n"
            f"{file_line}"
            f"📦 **Size:** `{cur_str}` / `{tot_str}`\n"
            f"⚡ **Speed:** `{spd_str}`\n"
            f"⏱️ **ETA:** `{eta_str}` | **Elapsed:** `{elapsed_str}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        try:
            await progress_message.edit(tg_text)
        except Exception:
            pass

    if is_finished and msg_id in _TRACKER_STATES:
        del _TRACKER_STATES[msg_id]

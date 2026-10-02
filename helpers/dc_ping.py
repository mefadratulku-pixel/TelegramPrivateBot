import time
import asyncio
import socket
from typing import Dict, List, Tuple
from rich.table import Table
from rich.console import Console
from rich import box

console = Console(highlight=False)

TG_DCS = {
    1: {"name": "DC1", "city": "Miami", "country": "USA", "code": "US", "flag": "🇺🇸", "ip": "149.154.175.53"},
    2: {"name": "DC2", "city": "Amsterdam", "country": "NL", "code": "NL", "flag": "🇳🇱", "ip": "149.154.167.51"},
    3: {"name": "DC3", "city": "Miami", "country": "USA", "code": "US", "flag": "🇺🇸", "ip": "149.154.175.100"},
    4: {"name": "DC4", "city": "Amsterdam", "country": "NL", "code": "NL", "flag": "🇳🇱", "ip": "149.154.167.91"},
    5: {"name": "DC5", "city": "Singapore", "country": "SG", "code": "SG", "flag": "🇸🇬", "ip": "91.108.56.130"},
}

def ping_tcp_single(ip: str, port: int = 443, timeout: float = 3.0, proxy_dict: dict = None) -> float:
    """Measures TCP handshake latency to a specific IP in milliseconds, through proxy if configured."""
    if proxy_dict:
        try:
            import socks
            proxy_type_map = {
                "socks4": socks.SOCKS4,
                "socks5": socks.SOCKS5,
                "http": socks.HTTP
            }
            ptype = proxy_type_map.get(str(proxy_dict.get("scheme", "http")).lower(), socks.HTTP)
            s = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
            s.set_proxy(
                proxy_type=ptype,
                addr=proxy_dict.get("hostname"),
                port=proxy_dict.get("port"),
                rdns=True,
                username=proxy_dict.get("username"),
                password=proxy_dict.get("password")
            )
            s.settimeout(timeout)
            start = time.perf_counter()
            s.connect((ip, port))
            latency = (time.perf_counter() - start) * 1000.0
            return round(latency, 1)
        except Exception:
            return -1.0
        finally:
            try:
                s.close()
            except Exception:
                pass
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        start = time.perf_counter()
        try:
            s.connect((ip, port))
            latency = (time.perf_counter() - start) * 1000.0
            return round(latency, 1)
        except Exception:
            return -1.0
        finally:
            s.close()

async def get_all_dc_pings(proxy_dict=None) -> List[Dict]:
    """Asynchronously measures latency to all 5 Telegram Data Centers."""
    if proxy_dict is None:
        try:
            from config import PyroConf
            proxy_dict = PyroConf.get_proxy()
        except Exception:
            proxy_dict = None

    loop = asyncio.get_running_loop()
    tasks = []
    for dc_id, info in TG_DCS.items():
        task = loop.run_in_executor(None, ping_tcp_single, info["ip"], 443, 3.5, proxy_dict)
        tasks.append((dc_id, info, task))
        
    results = []
    for dc_id, info, task in tasks:
        lat = await task
        results.append({
            "dc_id": dc_id,
            "name": info["name"],
            "city": info["city"],
            "country": info["country"],
            "code": info.get("code", info["country"]),
            "flag": info.get("flag", "🌐"),
            "location": f"{info['city']}, {info['country']}",
            "ip": info["ip"],
            "latency": lat
        })
    # Sort by latency (lowest first, timeouts at the end)
    results.sort(key=lambda x: x["latency"] if x["latency"] > 0 else 99999)
    return results

def build_compact_dc_table(results: List[Dict], user_dc: int = 0) -> Table:
    """Builds a 5-row compact DC latency table for the unified dashboard."""
    table = Table(box=None, show_header=False, padding=(0, 0), expand=True)
    table.add_column("dc", style="bold bright_white", width=12, no_wrap=True)
    table.add_column("ping", width=9, no_wrap=True)
    table.add_column("quality", no_wrap=True)

    # Order display: If user DC exists, prioritize it first, then others
    ordered = list(results) if results else []
    if not ordered:
        for dc_id in [5, 4, 2, 3, 1]:
            info = TG_DCS[dc_id]
            ordered.append({
                "dc_id": dc_id,
                "name": info["name"],
                "code": info["code"],
                "flag": info["flag"],
                "latency": 0.0
            })

    for item in ordered[:5]:
        dc_id = item.get("dc_id", 0)
        flag = item.get("flag", "🌐")
        name = item.get("name", f"DC{dc_id}")
        code = item.get("code", "")
        lat = item.get("latency", 0.0)
        is_user = (dc_id == user_dc)

        label = f"{flag} DC{dc_id} ({code})"
        if lat < 0:
            p_str = "[bold red]Timeout[/bold red]"
            s_str = "[red]✖ Down[/red]"
        elif lat == 0.0:
            p_str = "[dim]Testing...[/dim]"
            s_str = "[dim]Pending[/dim]"
        elif is_user:
            p_str = f"[bold green]{lat:>5.1f} ms[/bold green]"
            s_str = "[bold green]● Fast (You)[/bold green]"
        elif lat < 100:
            p_str = f"[bold green]{lat:>5.1f} ms[/bold green]"
            s_str = "[bold green]● Fast[/bold green]"
        elif lat < 250:
            p_str = f"[bold yellow]{lat:>5.1f} ms[/bold yellow]"
            s_str = "[yellow]● Normal[/yellow]"
        else:
            p_str = f"[bold red]{lat:>5.1f} ms[/bold red]"
            s_str = "[red]● Remote[/red]"

        table.add_row(label, p_str, s_str)
    return table

def get_dc_table_rich(results: List[Dict], user_dc: int = 0) -> Table:
    """Builds a rich console table for the terminal."""
    table = Table(
        title="[bold bright_yellow]⚡ TELEGRAM DATA CENTER LATENCY (TCP PING) ⚡[/bold bright_yellow]",
        box=box.ROUNDED,
        border_style="bright_blue",
        show_header=True,
        header_style="bold bright_white"
    )
    table.add_column("DC ID", style="bold cyan", justify="center", width=8)
    table.add_column("Location", style="bright_white", width=20)
    table.add_column("IP Address", style="dim", width=16)
    table.add_column("Latency", justify="right", width=12)
    table.add_column("Quality", justify="center", width=14)

    for item in results:
        lat = item["latency"]
        is_user = " [bold green](Your DC)[/bold green]" if item["dc_id"] == user_dc else ""
        dc_label = f"{item['name']}{is_user}"
        
        if lat < 0:
            lat_str = "[bold red]Timeout[/bold red]"
            qual_str = "[red]✖ Unreachable[/red]"
        elif lat < 100:
            lat_str = f"[bold green]{lat:.1f} ms[/bold green]"
            qual_str = "[bold green]🟢 Ultra Fast[/bold green]"
        elif lat < 250:
            lat_str = f"[bold yellow]{lat:.1f} ms[/bold yellow]"
            qual_str = "[yellow]🟡 Normal[/yellow]"
        else:
            lat_str = f"[bold red]{lat:.1f} ms[/bold red]"
            qual_str = "[red]🔴 High Latency[/red]"

        table.add_row(
            dc_label,
            item["location"],
            item["ip"],
            lat_str,
            qual_str
        )
    return table

async def generate_telegram_report(user_dc: int = 0, bot_dc: int = 0, server_ping_ms: float = 0.0) -> str:
    """Generates a clean markdown report for Telegram chat."""
    results = await get_all_dc_pings()
    
    user_info = TG_DCS.get(user_dc, {"name": f"DC{user_dc}", "city": "Unknown", "country": ""})
    bot_info = TG_DCS.get(bot_dc, {"name": f"DC{bot_dc}", "city": "Unknown", "country": ""})
    
    user_loc = f"{user_info['name']} ({user_info['city']}, {user_info['country']})" if user_dc else "Detecting..."
    bot_loc = f"{bot_info['name']} ({bot_info['city']}, {bot_info['country']})" if bot_dc else "Detecting..."
    
    try:
        from config import PyroConf
        proxy_info = PyroConf.get_proxy()
    except Exception:
        proxy_info = None

    routing_str = f"🚀 `BDIX HTTP ({PyroConf.PROXY_HOST})`" if proxy_info else "`Direct Connection`"

    lines = [
        "⚡ **TELEGRAM DATA CENTER PING & SPEED** ⚡",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"👤 **Your Account DC:** `{user_loc}`",
        f"🤖 **Bot Client DC:** `{bot_loc}`",
        f"🛡️ **Network Route:** {routing_str}",
        f"⏱️ **Bot Response Latency:** `{server_ping_ms:.1f} ms`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🌐 **Live DC Connectivity:**"
    ]
    
    for idx, r in enumerate(results):
        lat = r["latency"]
        dc_name = r["name"]
        loc = r["location"]
        is_mine = " ⭐️" if r["dc_id"] == user_dc else ""
        
        if lat < 0:
            badge = "🔴"
            status = "`Timeout`"
        elif lat < 100:
            badge = "🟢"
            status = f"`{lat:.1f} ms` [Fastest ⚡]" if idx == 0 else f"`{lat:.1f} ms`"
        elif lat < 250:
            badge = "🟡"
            status = f"`{lat:.1f} ms`"
        else:
            badge = "🔴"
            status = f"`{lat:.1f} ms`"
            
        lines.append(f"{badge} **{dc_name}** ({loc}){is_mine}: {status}")
        
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 *Tip: Lower ping to your account DC ensures faster downloads.*")
    return "\n".join(lines)

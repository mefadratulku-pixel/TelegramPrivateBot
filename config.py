import os
from os import getenv
from time import time
from dotenv import load_dotenv

try:
    load_dotenv("config.env.local", interpolate=False, override=True)
    load_dotenv("config.env", interpolate=False, override=True)
except:
    pass

if not getenv("BOT_TOKEN") or not getenv("BOT_TOKEN").count(":") == 1:
    print("Error: BOT_TOKEN must be in format '123456:abcdefghijklmnopqrstuvwxyz'")
    exit(1)

if (
    not getenv("SESSION_STRING")
    or getenv("SESSION_STRING") == "xxxxxxxxxxxxxxxxxxxxxxx"
):
    print("Error: SESSION_STRING must be set with a valid string")
    exit(1)


# Pyrogram setup
class PyroConf(object):
    API_ID = int(getenv("API_ID", "6"))
    API_HASH = getenv("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e")
    BOT_TOKEN = getenv("BOT_TOKEN")
    SESSION_STRING = getenv("SESSION_STRING")
    BOT_START_TIME = time()

    SAVE_DIR = getenv("SAVE_DIR", "SavedMedia")

    MAX_CONCURRENT_DOWNLOADS = int(getenv("MAX_CONCURRENT_DOWNLOADS", "1"))
    BATCH_SIZE = int(getenv("BATCH_SIZE", "1"))
    FLOOD_WAIT_DELAY = int(getenv("FLOOD_WAIT_DELAY", "10"))

    # BDIX / Local SOCKS5 or HTTP Proxy
    USE_PROXY = getenv("USE_PROXY", "false").strip().lower() in ("true", "1", "yes", "on")
    PROXY_SCHEME = getenv("PROXY_SCHEME", "http").lower()
    PROXY_HOST = getenv("PROXY_HOST", "").strip()
    PROXY_PORT = int(getenv("PROXY_PORT", "0")) if getenv("PROXY_PORT", "").strip().isdigit() else 0
    PROXY_USER = getenv("PROXY_USER", "").strip()
    PROXY_PASS = getenv("PROXY_PASS", "").strip()

    @classmethod
    def get_proxy(cls):
        if cls.USE_PROXY and cls.PROXY_HOST and cls.PROXY_PORT:
            p = {
                "scheme": cls.PROXY_SCHEME,
                "hostname": cls.PROXY_HOST,
                "port": cls.PROXY_PORT,
            }
            if cls.PROXY_USER:
                p["username"] = cls.PROXY_USER
            if cls.PROXY_PASS:
                p["password"] = cls.PROXY_PASS
            return p
        return None


def set_proxy_state(enabled: bool) -> bool:
    """Toggles USE_PROXY in config.env between True and False."""
    env_file = "config.env"
    if not os.path.exists(env_file):
        return False

    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    found = False
    new_lines = []
    val_str = "True" if enabled else "False"

    for line in lines:
        if line.strip().startswith("USE_PROXY"):
            new_lines.append(f"USE_PROXY = {val_str}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"\nUSE_PROXY = {val_str}\n")

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    PyroConf.USE_PROXY = enabled
    return enabled


def toggle_proxy_state() -> bool:
    """Flips the current proxy state in config.env."""
    return set_proxy_state(not PyroConf.USE_PROXY)

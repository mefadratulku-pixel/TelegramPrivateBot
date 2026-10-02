import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler

# UTF-8 terminal support
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# removing old logs file if they exist.
try:
    os.remove("logs.txt")
except:
    pass

file_handler = RotatingFileHandler("logs.txt", mode="w+", maxBytes=5000000, backupCount=10, encoding="utf-8")
file_handler.setFormatter(logging.Formatter(
    "[%(asctime)s - %(levelname)s] - %(funcName)s() - Line %(lineno)d: %(name)s - %(message)s",
    datefmt="%d-%b-%y %I:%M:%S %p"
))

rich_handler = RichHandler(
    rich_tracebacks=True,
    show_time=False,
    show_path=False,
    markup=True,
)
rich_handler.setLevel(logging.ERROR)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, rich_handler]
)

logging.getLogger("pyrogram").setLevel(logging.ERROR)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)

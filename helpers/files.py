# Copyright (C) @TheSmartBisnu
# Channel: https://t.me/itsSmartDev

import os
import shutil
from typing import Optional

from logger import LOGGER

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]

def get_download_path(folder_id: int, filename: str, root_dir: str = "downloads") -> str:
    folder = os.path.join(root_dir, str(folder_id))
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, filename)


# Map media type keywords to folder names
MEDIA_TYPE_FOLDERS = {
    "photo": "Photos",
    "video": "Videos",
    "audio": "Audio",
    "document": "Documents",
}


def file_exists_in_save_dir(save_dir: str, channel_name: str, filename: str, media_type: str = "document") -> str:
    """Return the exact destination path if it exists, otherwise None."""
    type_folder = MEDIA_TYPE_FOLDERS.get(media_type, "Documents")
    dest = os.path.join(save_dir, channel_name, type_folder, filename)
    if os.path.exists(dest):
        return dest
    return None


def get_save_path(save_dir: str, channel_name: str, filename: str, media_type: str = "document") -> str:
    """Return path like SavedMedia/<channel_name>/Videos/<filename>, creating dirs as needed."""
    type_folder = MEDIA_TYPE_FOLDERS.get(media_type, "Documents")
    folder = os.path.join(save_dir, channel_name, type_folder)
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, filename)
    # Avoid overwriting: append _1, _2, etc.
    if os.path.exists(dest):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest):
            dest = os.path.join(folder, f"{base}_{counter}{ext}")
            counter += 1
    return dest


def cleanup_download(path: str) -> None:
    try:
        LOGGER(__name__).info(f"Cleaning Download: {path}")
        
        if os.path.exists(path):
            os.remove(path)
        if os.path.exists(path + ".temp"):
            os.remove(path + ".temp")

        folder = os.path.dirname(path)
        if os.path.isdir(folder) and not os.listdir(folder):
            os.rmdir(folder)

    except Exception as e:
        LOGGER(__name__).error(f"Cleanup failed for {path}: {e}")


def cleanup_downloads_root(root_dir: str = "downloads") -> tuple[int, int]:
    if not os.path.isdir(root_dir):
        return 0, 0

    file_count = 0
    total_size = 0
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            file_count += 1
            try:
                total_size += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass

    shutil.rmtree(root_dir, ignore_errors=True)
    return file_count, total_size


def get_readable_file_size(size_in_bytes: Optional[float]) -> str:
    if size_in_bytes is None or size_in_bytes < 0:
        return "0B"

    for unit in SIZE_UNITS:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024

    return "File too large"


def get_readable_time(seconds: int) -> str:
    result = ""
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days:
        result += f"{days}d"
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours:
        result += f"{hours}h"
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes:
        result += f"{minutes}m"
    seconds = int(seconds)
    result += f"{seconds}s"
    return result


async def fileSizeLimit(file_size, message, action_type="download", is_premium=False):
    MAX_FILE_SIZE = 2 * 2097152000 if is_premium else 2097152000
    if file_size > MAX_FILE_SIZE:
        await message.reply(
            f"The file size exceeds the {get_readable_file_size(MAX_FILE_SIZE)} limit and cannot be {action_type}ed."
        )
        return False
    return True

import os
import shutil
import asyncio
from time import time
from PIL import Image
from logger import LOGGER
from typing import Optional
from asyncio.subprocess import PIPE
from asyncio import create_subprocess_exec, create_subprocess_shell, wait_for

from pyleaves import Leaves
from pyrogram.parser import Parser
from pyrogram.utils import get_channel_id
from pyrogram.errors import FloodWait
from pyrogram.types import (
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    InputMediaAudio,
    Voice,
)

from helpers.files import (
    fileSizeLimit,
    cleanup_download,
    get_save_path
)

from helpers.msg import (
    get_parsed_msg,
    get_channel_name
)

from config import PyroConf
from helpers.tracker import candy_progress

# Progress bar template
PROGRESS_BAR = """
Percentage: {percentage:.2f}% | {current}/{total}
Speed: {speed}/s
Estimated Time Left: {est_time} seconds
"""

async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
    else:
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await proc.communicate()
    try:
        stdout = stdout.decode().strip()
    except:
        stdout = "Unable to decode the response!"
    try:
        stderr = stderr.decode().strip()
    except:
        stderr = "Unable to decode the error!"
    return stdout, stderr, proc.returncode


async def get_media_info(path):
    try:
        result = await cmd_exec([
            "ffprobe", "-hide_banner", "-loglevel", "error",
            "-print_format", "json", "-show_format", "-show_streams", path,
        ])
    except Exception as e:
        LOGGER(__name__).error(f"Get Media Info: {e}. File: {path}")
        return 0, None, None, None, None

    if result[0] and result[2] == 0:
        try:
            import json
            data = json.loads(result[0])

            fields = data.get("format", {})
            duration = round(float(fields.get("duration", 0)))

            tags = fields.get("tags", {})
            artist = tags.get("artist") or tags.get("ARTIST") or tags.get("Artist")
            title = tags.get("title") or tags.get("TITLE") or tags.get("Title")

            width = None
            height = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    width = stream.get("width")
                    height = stream.get("height")
                    break

            return duration, artist, title, width, height
        except Exception as e:
            LOGGER(__name__).error(f"Error parsing media info: {e}")
            return 0, None, None, None, None
    return 0, None, None, None, None


async def get_video_thumbnail(video_file, duration):
    os.makedirs("Assets", exist_ok=True)
    output = os.path.join("Assets", "video_thumb.jpg")

    if duration is None:
        duration = (await get_media_info(video_file))[0]
    if not duration:
        duration = 3
    duration //= 2

    if os.path.exists(output):
        try:
            os.remove(output)
        except:
            pass

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-ss", str(duration), "-i", video_file,
        "-vframes", "1", "-q:v", "2",
        "-y", output,
    ]
    try:
        _, err, code = await wait_for(cmd_exec(cmd), timeout=60)
        if code != 0 or not os.path.exists(output):
            LOGGER(__name__).warning(f"Thumbnail generation failed: {err}")
            return None
    except Exception as e:
        LOGGER(__name__).warning(f"Thumbnail generation error: {e}")
        return None
    return output


# Generate progress bar for downloading/uploading
def progressArgs(action: str, progress_message, start_time):
    return (action, progress_message, start_time, PROGRESS_BAR, "▓", "░")


async def send_media(
    bot, message, media_path, media_type, caption, progress_message, start_time
):
    file_size = os.path.getsize(media_path)

    if not await fileSizeLimit(file_size, message, "upload"):
        return

    progress_args = progressArgs("📥 Uploading Progress", progress_message, start_time)
    LOGGER(__name__).info(f"Uploading media: {media_path} ({media_type})")

    async def _send_once():
        if media_type == "photo":
            await message.reply_photo(
                media_path,
                caption=caption or "",
                progress=Leaves.progress_for_pyrogram,
                progress_args=progress_args,
            )
            return
        if media_type == "video":
            duration, _, _, width, height = await get_media_info(media_path)

            if not duration or duration == 0:
                duration = 0
                LOGGER(__name__).warning(f"Could not extract duration for {media_path}")

            if not width or not height:
                width = 640
                height = 480

            thumb = await get_video_thumbnail(media_path, duration)

            await message.reply_video(
                media_path,
                duration=duration,
                width=width,
                height=height,
                thumb=thumb,
                caption=caption or "",
                supports_streaming=True,
                progress=Leaves.progress_for_pyrogram,
                progress_args=progress_args,
            )
            if thumb:
                cleanup_download(thumb)
            return
        if media_type == "audio":
            duration, artist, title, _, _ = await get_media_info(media_path)
            await message.reply_audio(
                media_path,
                duration=duration,
                performer=artist,
                title=title,
                caption=caption or "",
                progress=Leaves.progress_for_pyrogram,
                progress_args=progress_args,
            )
            return
        if media_type == "document":
            await message.reply_document(
                media_path,
                caption=caption or "",
                progress=Leaves.progress_for_pyrogram,
                progress_args=progress_args,
            )

    for attempt in range(2):
        try:
            await _send_once()
            return
        except FloodWait as e:
            wait_s = int(getattr(e, "value", 0) or 0)
            LOGGER(__name__).warning(f"FloodWait while uploading media: {wait_s}s")
            if wait_s > 0 and attempt == 0:
                await asyncio.sleep(wait_s + 1)
                continue
            raise


async def download_single_media(msg, progress_message, start_time):
    for attempt in range(2):
        try:
            media_path = await msg.download(
                progress=candy_progress,
                progress_args=("📥 Downloading", progress_message, start_time, getattr(msg, "file_name", "") or "Media"),
            )

            parsed_caption = await get_parsed_msg(
                msg.caption or "", msg.caption_entities
            )

            if msg.photo:
                return ("success", media_path, InputMediaPhoto(media=media_path, caption=parsed_caption))
            if msg.video:
                return ("success", media_path, InputMediaVideo(media=media_path, caption=parsed_caption))
            if msg.document:
                return ("success", media_path, InputMediaDocument(media=media_path, caption=parsed_caption))
            if msg.audio:
                return ("success", media_path, InputMediaAudio(media=media_path, caption=parsed_caption))

        except FloodWait as e:
            wait_s = int(getattr(e, "value", 0) or 0)
            LOGGER(__name__).warning(f"FloodWait while downloading media: {wait_s}s")
            if wait_s > 0 and attempt == 0:
                await asyncio.sleep(wait_s + 1)
                continue
            return ("error", None, None)
        except Exception as e:
            LOGGER(__name__).info(f"Error downloading media: {e}")
            return ("error", None, None)

    return ("skip", None, None)


async def processMediaGroup(chat_message, bot, message, post_url=""):
    channel_name = get_channel_name(post_url) if post_url else "unknown_channel"
    media_group_messages = await chat_message.get_media_group()
    temp_paths = []

    start_time = time()
    progress_message = await message.reply("📥 Downloading media group...")
    LOGGER(__name__).info(
        f"Downloading media group with {len(media_group_messages)} items..."
    )

    download_tasks = []
    for msg in media_group_messages:
        if msg.photo or msg.video or msg.document or msg.audio:
            download_tasks.append(download_single_media(msg, progress_message, start_time))

    results = await asyncio.gather(*download_tasks, return_exceptions=True)

    saved_files = []
    for result in results:
        if isinstance(result, Exception):
            LOGGER(__name__).error(f"Download task failed: {result}")
            continue

        status, media_path, media_obj = result
        if status == "success" and media_path:
            temp_paths.append(media_path)
            # Detect media type from the InputMedia object
            if isinstance(media_obj, InputMediaPhoto):
                m_type = "photo"
            elif isinstance(media_obj, InputMediaVideo):
                m_type = "video"
            elif isinstance(media_obj, InputMediaAudio):
                m_type = "audio"
            else:
                m_type = "document"
            
            # Use get_file_name to get the ideal filename (with caption)
            from helpers.msg import get_file_name
            # For media groups, we can use the caption of the first media if the current one has none
            ideal_filename = get_file_name(chat_message.id, chat_message, caption=chat_message.caption or chat_message.text)
            
            # Since msg.download () generates a random/internal temp file name, we need to extract the IDEAL extension
            _, temp_ext = os.path.splitext(media_path)
            # Replace the ideal filename's extension with the actual downloaded extension to perfectly match
            ideal_base, _ = os.path.splitext(ideal_filename)
            final_filename = f"{ideal_base}{temp_ext}"
            
            # Check for duplicate
            file_size = os.path.getsize(media_path)
            
            # Use main's duplicate checker
            from main import check_duplicate_and_prompt
            
            is_allowed = await check_duplicate_and_prompt(
                bot, message, channel_name, final_filename, m_type, file_size, progress_message
            )
            
            if not is_allowed:
                cleanup_download(media_path)
                continue
                
            # Move to save directory with the new name
            save_dest = get_save_path(PyroConf.SAVE_DIR, channel_name, final_filename, m_type)
            shutil.move(media_path, save_dest)
            saved_files.append(save_dest)
            LOGGER(__name__).info(f"Saved: {save_dest}")
        elif status == "error" and media_path:
            cleanup_download(media_path)

    # Clean up any remaining temp files/dirs
    for path in temp_paths:
        cleanup_download(path)

    if saved_files:
        file_list = "\n".join([f"📁 `{f}`" for f in saved_files])
        await progress_message.edit(
            f"**✅ Media group saved locally! ({len(saved_files)} files)**\n{file_list}"
        )
        return True

    await progress_message.edit("❌ No valid media saved from the media group.")
    return False

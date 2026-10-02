# Copyright (C) @TheSmartBisnu
# Channel: https://t.me/itsSmartDev

from pyrogram.parser import Parser
from pyrogram.utils import get_channel_id


async def get_parsed_msg(text, entities):
    return Parser.unparse(text, entities or [], is_html=False)
    

def get_channel_name(link: str) -> str:
    """Extract a folder-safe channel name from a Telegram post URL."""
    parts = link.split("/")
    # Private channel: https://t.me/c/12345/msg_id
    if len(parts) >= 6 and parts[3] == "c":
        return f"c_{parts[4]}"
    # Public channel: https://t.me/channelname/msg_id
    if len(parts) >= 5:
        name = parts[3]
        if name == "c":
            return f"c_{parts[4]}"
        return name
    return "unknown_channel"


def getChatMsgID(link: str):
    linkps = link.split("/")
    chat_id, message_thread_id, message_id = None, None, None
    
    try:
        if len(linkps) == 7 and linkps[3] == "c":
            chat_id = get_channel_id(int(linkps[4]))
            message_thread_id = int(linkps[5])
            message_id = int(linkps[6])
        elif len(linkps) == 6:
            if linkps[3] == "c":
                chat_id = get_channel_id(int(linkps[4]))
                message_id = int(linkps[5])
            else:
                chat_id = linkps[3]
                message_thread_id = int(linkps[4])
                message_id = int(linkps[5])
        elif len(linkps) == 5:
            chat_id = linkps[3]
            if chat_id == "m":
                raise ValueError("Invalid ClientType used to parse this message link")
            message_id = int(linkps[4])
    except (ValueError, TypeError):
        raise ValueError("Invalid post URL. Must end with a numeric ID.")

    if not chat_id or not message_id:
        raise ValueError("Please send a valid Telegram post URL.")

    return chat_id, message_id


import re
import os

def sanitize_filename(text: str, max_length: int = 50) -> str:
    """Sanitize text to be safe for filenames."""
    if not text:
        return ""
    # Remove invalid characters
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    # Replace newlines and tabs with spaces
    text = re.sub(r'[\n\r\t]+', " ", text)
    text = text.strip()
    return text[:max_length].strip()


def get_file_name(message_id: int, chat_message, caption: str = "") -> str:
    # Use provided caption or fallback to message's own caption/text
    full_text = caption or chat_message.caption or chat_message.text or ""
    prefix = sanitize_filename(full_text)
    
    base_name = f"{message_id}"
    
    if chat_message.document:
        base_name = chat_message.document.file_name
    elif chat_message.video:
        base_name = chat_message.video.file_name or f"{message_id}.mp4"
    elif chat_message.audio:
        base_name = chat_message.audio.file_name or f"{message_id}.mp3"
    elif chat_message.voice:
        base_name = f"{message_id}.ogg"
    elif chat_message.video_note:
        base_name = f"{message_id}.mp4"
    elif chat_message.animation:
        base_name = chat_message.animation.file_name or f"{message_id}.gif"
    elif chat_message.sticker:
        if chat_message.sticker.is_animated:
            base_name = f"{message_id}.tgs"
        elif chat_message.sticker.is_video:
            base_name = f"{message_id}.webm"
        else:
            base_name = f"{message_id}.webp"
    elif chat_message.photo:
        base_name = f"{message_id}.jpg"
        
    if prefix:
        # Prepend the sanitized caption
        base, ext = os.path.splitext(base_name)
        return f"{prefix} - {base}{ext}"
    return base_name

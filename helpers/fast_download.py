import os
import time
import math
import asyncio
from typing import Optional, Callable
from pyrogram import Client, raw
from pyrogram.session import Session, Auth
from pyrogram.file_id import FileId, FileType
from logger import LOGGER

async def fast_download_file(
    client: Client,
    chat_message,
    file_name: str,
    progress: Optional[Callable] = None,
    progress_args: tuple = (),
    max_workers: int = 12,
    chunk_size: int = 1024 * 1024
) -> Optional[str]:
    """
    High-Speed Multi-Chunk Pipelined Downloader for Telegram Media.
    Bypasses Pyrogram's sequential 1MB bottleneck by running parallel chunk
    streams directly to the Telegram Data Center.
    """
    media = (
        chat_message.video
        or chat_message.document
        or chat_message.audio
        or chat_message.photo
    )
    if not media:
        # Fallback to standard download
        return await chat_message.download(file_name=file_name, progress=progress, progress_args=progress_args)

    file_size = getattr(media, "file_size", 0) or 0
    # For small files (< 5 MB), standard download is already fast and has zero overhead
    if file_size < 5 * 1024 * 1024:
        return await chat_message.download(file_name=file_name, progress=progress, progress_args=progress_args)

    try:
        file_id_obj = FileId.decode(media.file_id)
        dc_id = file_id_obj.dc_id
        file_type = file_id_obj.file_type

        if file_type == FileType.PHOTO:
            location = raw.types.InputPhotoFileLocation(
                id=file_id_obj.media_id,
                access_hash=file_id_obj.access_hash,
                file_reference=file_id_obj.file_reference,
                thumb_size=file_id_obj.thumbnail_size
            )
        else:
            location = raw.types.InputDocumentFileLocation(
                id=file_id_obj.media_id,
                access_hash=file_id_obj.access_hash,
                file_reference=file_id_obj.file_reference,
                thumb_size=""
            )

        # Ensure destination directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_name)), exist_ok=True)
        temp_file = os.path.abspath(file_name) + ".temp"

        # Pre-allocate sparse file for out-of-order parallel chunk writing
        with open(temp_file, "wb") as fp:
            if file_size > 0:
                fp.seek(file_size - 1)
                fp.write(b"\0")

        # Establish high-speed media sessions to the specific target DC
        auth_key = await Auth(client, dc_id, await client.storage.test_mode()).create() if dc_id != await client.storage.dc_id() else await client.storage.auth_key()
        session = Session(client, dc_id, auth_key, await client.storage.test_mode(), is_media=True)
        await session.start()

        if dc_id != await client.storage.dc_id():
            exported_auth = await client.invoke(raw.functions.auth.ExportAuthorization(dc_id=dc_id))
            await session.invoke(raw.functions.auth.ImportAuthorization(id=exported_auth.id, bytes=exported_auth.bytes))

        total_chunks = math.ceil(file_size / chunk_size)
        sem = asyncio.Semaphore(max_workers)
        write_lock = asyncio.Lock()
        downloaded = 0
        file_handle = open(temp_file, "r+b")

        async def fetch_chunk(chunk_idx: int):
            nonlocal downloaded
            offset = chunk_idx * chunk_size
            limit = min(chunk_size, file_size - offset) if file_size > 0 else chunk_size

            for attempt in range(3):
                try:
                    async with sem:
                        res = await session.invoke(
                            raw.functions.upload.GetFile(
                                location=location,
                                offset=offset,
                                limit=limit
                            ),
                            sleep_threshold=30
                        )

                    if isinstance(res, raw.types.upload.File):
                        data = res.bytes
                        async with write_lock:
                            file_handle.seek(offset)
                            file_handle.write(data)

                        downloaded += len(data)
                        if progress:
                            try:
                                await progress(downloaded, file_size, *progress_args)
                            except Exception:
                                pass
                        return
                except Exception as ex:
                    if attempt == 2:
                        raise ex
                    await asyncio.sleep(0.5)

        try:
            tasks = [fetch_chunk(i) for i in range(total_chunks)]
            await asyncio.gather(*tasks)
        finally:
            file_handle.close()
            await session.stop()

        # Finalize file rename from .temp
        if os.path.exists(file_name):
            os.remove(file_name)
        os.rename(temp_file, file_name)
        return file_name

    except Exception as e:
        LOGGER(__name__).warning(f"Fast downloader encountered {e}, falling back to default engine...")
        # Clean up any partial temp file
        if 'temp_file' in locals() and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        # Seamless fallback to standard Pyrogram download
        return await chat_message.download(file_name=file_name, progress=progress, progress_args=progress_args)

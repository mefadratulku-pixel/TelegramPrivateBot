import os
import sqlite3
import time
from typing import Optional, Tuple
from helpers.files import MEDIA_TYPE_FOLDERS
from config import PyroConf

class DuplicateManager:
    def __init__(self, db_path: str = "downloads_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id TEXT,
                        message_id INTEGER,
                        channel_name TEXT,
                        filename TEXT,
                        media_type TEXT,
                        file_size INTEGER,
                        save_path TEXT,
                        downloaded_at REAL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_msg ON downloads(chat_id, message_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_file ON downloads(filename, file_size)")
        except Exception:
            pass

    def check_duplicate(
        self,
        channel_name: str,
        filename: str,
        media_type: str = "document",
        file_size: Optional[int] = None,
        chat_id: Optional[str] = None,
        message_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Instantly checks if a file is already downloaded before starting the download.
        Returns: (is_duplicate: bool, existing_path: str or None)
        """
        # 1. Check SQLite database by Telegram post ID
        if chat_id and message_id:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT save_path FROM downloads WHERE chat_id = ? AND message_id = ?",
                        (str(chat_id), int(message_id))
                    )
                    row = cur.fetchone()
                    if row and row[0] and os.path.exists(row[0]):
                        return True, row[0]
            except Exception:
                pass

        # 2. Check local filesystem in SavedMedia folder
        type_folder = MEDIA_TYPE_FOLDERS.get(media_type, "Documents")
        target_path = os.path.join(PyroConf.SAVE_DIR, channel_name, type_folder, filename)
        if os.path.exists(target_path):
            existing_size = os.path.getsize(target_path)
            # If expected size is known and matches
            if not file_size or abs(existing_size - file_size) <= 1024:
                return True, target_path

        # 3. Check SQLite database by filename & file_size
        if filename and file_size:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT save_path FROM downloads WHERE filename = ? AND file_size = ?",
                        (filename, int(file_size))
                    )
                    row = cur.fetchone()
                    if row and row[0] and os.path.exists(row[0]):
                        return True, row[0]
            except Exception:
                pass

        return False, None

    def record_download(
        self,
        chat_id: Optional[str],
        message_id: Optional[int],
        channel_name: str,
        filename: str,
        media_type: str,
        file_size: int,
        save_path: str
    ):
        """Records a successful download to the history database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO downloads
                    (chat_id, message_id, channel_name, filename, media_type, file_size, save_path, downloaded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(chat_id) if chat_id else None,
                    int(message_id) if message_id else None,
                    channel_name,
                    filename,
                    media_type,
                    int(file_size) if file_size else 0,
                    save_path,
                    time.time()
                ))
        except Exception:
            pass

    def get_stats(self) -> dict:
        """Returns statistics on total downloaded files and storage."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM downloads")
                count, total_bytes = cur.fetchone()
                return {"total_downloads": count or 0, "total_bytes": total_bytes or 0}
        except Exception:
            return {"total_downloads": 0, "total_bytes": 0}

dup_manager = DuplicateManager()

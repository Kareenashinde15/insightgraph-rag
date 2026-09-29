"""Small SQLite persistence layer for the single-user local application."""

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "knowledge.db"


class LocalDatabase:
    def __init__(self, path: str | None = None):
        configured_path = path or os.getenv("LOCAL_DB_PATH")
        self.path = Path(configured_path) if configured_path else DEFAULT_DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            self.path,
            check_same_thread=False,
            timeout=30,
        )
        self._connection.row_factory = sqlite3.Row
        with self._lock:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    collection TEXT NOT NULL,
                    record_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (collection, record_key)
                )
                """
            )
            self._connection.commit()

    def load(self, collection: str) -> Dict[str, Any]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT record_key, payload FROM records WHERE collection = ?",
                (collection,),
            ).fetchall()
        return {row["record_key"]: json.loads(row["payload"]) for row in rows}

    def upsert(self, collection: str, record_key: str, payload: Any) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO records(collection, record_key, payload)
                VALUES (?, ?, ?)
                ON CONFLICT(collection, record_key)
                DO UPDATE SET payload = excluded.payload
                """,
                (collection, record_key, json.dumps(payload, default=str)),
            )
            self._connection.commit()

    def delete(self, collection: str, record_key: str) -> None:
        with self._lock:
            self._connection.execute(
                "DELETE FROM records WHERE collection = ? AND record_key = ?",
                (collection, record_key),
            )
            self._connection.commit()

    def clear(self, collection: str) -> None:
        with self._lock:
            self._connection.execute("DELETE FROM records WHERE collection = ?", (collection,))
            self._connection.commit()

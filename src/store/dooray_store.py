from __future__ import annotations

import sqlite3
from pathlib import Path


class DoorayStore:
    def __init__(self, db_path: Path | str = ":memory:") -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS dooray_user_mapping (
                slack_user_id TEXT PRIMARY KEY,
                dooray_member_id TEXT NOT NULL
            );
        """)

    def set_user_mapping(self, slack_user_id: str, dooray_member_id: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO dooray_user_mapping (slack_user_id, dooray_member_id) VALUES (?, ?)",
            (slack_user_id, dooray_member_id),
        )
        self._conn.commit()

    def get_dooray_member_id(self, slack_user_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT dooray_member_id FROM dooray_user_mapping WHERE slack_user_id = ?",
            (slack_user_id,),
        ).fetchone()
        if row is None:
            return None
        return str(row["dooray_member_id"])

    def remove_user_mapping(self, slack_user_id: str) -> None:
        self._conn.execute(
            "DELETE FROM dooray_user_mapping WHERE slack_user_id = ?",
            (slack_user_id,),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

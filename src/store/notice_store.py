from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from src.store.models import AttendanceStatus, MeetingNotice, Notice, NoticeType


class NoticeStore:
    def __init__(self, db_path: Path | str = ":memory:") -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS notices (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message_ts TEXT NOT NULL DEFAULT '',
                author_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                meeting_datetime TEXT,
                location TEXT,
                agenda TEXT
            );
            CREATE TABLE IF NOT EXISTS notice_responses (
                notice_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                response_type TEXT NOT NULL,
                responded_at REAL NOT NULL,
                PRIMARY KEY (notice_id, user_id),
                FOREIGN KEY (notice_id) REFERENCES notices(id)
            );
            CREATE TABLE IF NOT EXISTS remind_excludes (
                user_id TEXT PRIMARY KEY
            );
        """)

    def create_notice(self, notice: Notice) -> None:
        self._conn.execute(
            """INSERT INTO notices (id, type, title, content, channel_id, message_ts, author_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                notice.notice_id,
                notice.notice_type.value,
                notice.title,
                notice.content,
                notice.channel_id,
                notice.message_ts,
                notice.author_id,
                notice.created_at,
            ),
        )
        self._conn.commit()

    def create_meeting_notice(self, notice: MeetingNotice) -> None:
        self._conn.execute(
            """INSERT INTO notices
               (id, type, title, content, channel_id, message_ts, author_id, created_at,
                meeting_datetime, location, agenda)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                notice.notice_id,
                notice.notice_type.value,
                notice.title,
                notice.content,
                notice.channel_id,
                notice.message_ts,
                notice.author_id,
                notice.created_at,
                notice.meeting_datetime,
                notice.location,
                notice.agenda,
            ),
        )
        self._conn.commit()

    def update_notice(self, notice_id: str, title: str, content: str) -> None:
        self._conn.execute(
            "UPDATE notices SET title = ?, content = ? WHERE id = ?",
            (title, content, notice_id),
        )
        self._conn.commit()

    def update_meeting_notice(
        self,
        notice_id: str,
        title: str,
        meeting_datetime: str,
        location: str,
        agenda: str,
    ) -> None:
        self._conn.execute(
            "UPDATE notices SET title = ?, content = ?, meeting_datetime = ?, location = ?, agenda = ? WHERE id = ?",
            (title, f"회의: {title}", meeting_datetime, location, agenda, notice_id),
        )
        self._conn.commit()

    def update_message_ts(self, notice_id: str, message_ts: str) -> None:
        self._conn.execute(
            "UPDATE notices SET message_ts = ? WHERE id = ?",
            (message_ts, notice_id),
        )
        self._conn.commit()

    def get_notice(self, notice_id: str) -> Notice | MeetingNotice | None:
        row = self._conn.execute("SELECT * FROM notices WHERE id = ?", (notice_id,)).fetchone()
        if row is None:
            return None

        responses = self._conn.execute(
            "SELECT user_id, response_type FROM notice_responses WHERE notice_id = ?",
            (notice_id,),
        ).fetchall()

        notice_type = NoticeType(row["type"])

        if notice_type == NoticeType.MEETING:
            attendance: dict[str, AttendanceStatus] = {}
            for resp in responses:
                if resp["response_type"] in {s.value for s in AttendanceStatus}:
                    attendance[resp["user_id"]] = AttendanceStatus(resp["response_type"])

            return MeetingNotice(
                notice_id=row["id"],
                notice_type=notice_type,
                title=row["title"],
                content=row["content"],
                channel_id=row["channel_id"],
                message_ts=row["message_ts"],
                author_id=row["author_id"],
                created_at=row["created_at"],
                meeting_datetime=row["meeting_datetime"] or "",
                location=row["location"] or "",
                agenda=row["agenda"] or "",
                attendance=attendance,
            )

        read_by = [resp["user_id"] for resp in responses if resp["response_type"] == "read"]

        return Notice(
            notice_id=row["id"],
            notice_type=notice_type,
            title=row["title"],
            content=row["content"],
            channel_id=row["channel_id"],
            message_ts=row["message_ts"],
            author_id=row["author_id"],
            created_at=row["created_at"],
            read_by=read_by,
        )

    def list_notices(
        self,
        channel_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Notice | MeetingNotice]:
        if channel_id:
            rows = self._conn.execute(
                "SELECT id FROM notices WHERE channel_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (channel_id, limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id FROM notices ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()

        notices: list[Notice | MeetingNotice] = []
        for row in rows:
            notice = self.get_notice(row["id"])
            if notice is not None:
                notices.append(notice)
        return notices

    def count_notices(self, channel_id: str | None = None) -> int:
        if channel_id:
            row = self._conn.execute(
                "SELECT COUNT(*) AS cnt FROM notices WHERE channel_id = ?",
                (channel_id,),
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) AS cnt FROM notices").fetchone()
        return int(row["cnt"]) if row else 0

    def mark_read(self, notice_id: str, user_id: str) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO notice_responses (notice_id, user_id, response_type, responded_at)
               VALUES (?, ?, 'read', ?)""",
            (notice_id, user_id, time.time()),
        )
        self._conn.commit()

    def set_attendance(self, notice_id: str, user_id: str, status: AttendanceStatus) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO notice_responses (notice_id, user_id, response_type, responded_at)
               VALUES (?, ?, ?, ?)""",
            (notice_id, user_id, status.value, time.time()),
        )
        self._conn.commit()

    def add_remind_exclude(self, user_id: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO remind_excludes (user_id) VALUES (?)",
            (user_id,),
        )
        self._conn.commit()

    def remove_remind_exclude(self, user_id: str) -> None:
        self._conn.execute("DELETE FROM remind_excludes WHERE user_id = ?", (user_id,))
        self._conn.commit()

    def list_remind_excludes(self) -> list[str]:
        rows = self._conn.execute("SELECT user_id FROM remind_excludes").fetchall()
        return [row["user_id"] for row in rows]

    def close(self) -> None:
        self._conn.close()

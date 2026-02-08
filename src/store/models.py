from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from enum import StrEnum


class NoticeType(StrEnum):
    GENERAL = "general"
    MEETING = "meeting"


class AttendanceStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    ABSENT = "absent"


def generate_notice_id() -> str:
    ts = int(time.time())
    hex_part = secrets.token_hex(4)
    return f"notice_{ts}_{hex_part}"


@dataclass
class Notice:
    notice_id: str
    notice_type: NoticeType
    title: str
    content: str
    channel_id: str
    author_id: str
    created_at: float
    message_ts: str = ""
    read_by: list[str] = field(default_factory=list)

    def is_read_by(self, user_id: str) -> bool:
        return user_id in self.read_by

    def mark_read(self, user_id: str) -> None:
        if user_id not in self.read_by:
            self.read_by.append(user_id)


@dataclass
class MeetingNotice(Notice):
    meeting_datetime: str = ""
    location: str = ""
    agenda: str = ""
    attendance: dict[str, AttendanceStatus] = field(default_factory=dict)

    def get_attendance(self, user_id: str) -> AttendanceStatus | None:
        return self.attendance.get(user_id)

    def set_attendance(self, user_id: str, status: AttendanceStatus) -> None:
        self.attendance[user_id] = status

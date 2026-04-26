from __future__ import annotations

import time

import structlog
from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient

from src.store.models import (
    AttendanceStatus,
    MeetingNotice,
    Notice,
    NoticeType,
    generate_notice_id,
)
from src.store.notice_store import NoticeStore
from src.views.notice_views import (
    build_meeting_notice_message,
    build_notice_message,
)


def _build_message_link(channel_id: str, message_ts: str) -> str:
    ts_nodot = message_ts.replace(".", "")
    return f"https://slack.com/archives/{channel_id}/p{ts_nodot}"


logger = structlog.get_logger()


class NoticeService:
    def __init__(self, store: NoticeStore, client: WebClient) -> None:
        self._store = store
        self._client = client

    def create_and_post_notice(
        self,
        *,
        title: str,
        content: str,
        channel_id: str,
        author_id: str,
    ) -> Notice:
        notice = Notice(
            notice_id=generate_notice_id(),
            notice_type=NoticeType.GENERAL,
            title=title,
            content=content,
            channel_id=channel_id,
            author_id=author_id,
            created_at=time.time(),
        )

        msg = build_notice_message(notice)
        result = self._client.chat_postMessage(channel=channel_id, **msg)
        notice.message_ts = result.get("ts", "")

        self._store.create_notice(notice)
        self._store.update_message_ts(notice.notice_id, notice.message_ts)

        return notice

    def create_and_post_meeting_notice(
        self,
        *,
        title: str,
        channel_id: str,
        author_id: str,
        meeting_datetime: str,
        location: str,
        agenda: str,
    ) -> MeetingNotice:
        notice = MeetingNotice(
            notice_id=generate_notice_id(),
            notice_type=NoticeType.MEETING,
            title=title,
            content=f"회의: {title}",
            channel_id=channel_id,
            author_id=author_id,
            created_at=time.time(),
            meeting_datetime=meeting_datetime,
            location=location,
            agenda=agenda,
        )

        msg = build_meeting_notice_message(notice)
        result = self._client.chat_postMessage(channel=channel_id, **msg)
        notice.message_ts = result.get("ts", "")

        self._store.create_meeting_notice(notice)
        self._store.update_message_ts(notice.notice_id, notice.message_ts)

        return notice

    def update_and_repost_notice(
        self,
        notice_id: str,
        title: str,
        content: str,
    ) -> None:
        self._store.update_notice(notice_id, title, content)
        notice = self._store.get_notice(notice_id)
        if notice is None:
            return

        msg = build_notice_message(notice)
        self._client.chat_update(
            channel=notice.channel_id,
            ts=notice.message_ts,
            **msg,
        )

    def update_and_repost_meeting_notice(
        self,
        notice_id: str,
        title: str,
        meeting_datetime: str,
        location: str,
        agenda: str,
    ) -> None:
        self._store.update_meeting_notice(notice_id, title, meeting_datetime, location, agenda)
        notice = self._store.get_notice(notice_id)
        if notice is None or not isinstance(notice, MeetingNotice):
            return

        msg = build_meeting_notice_message(notice)
        self._client.chat_update(
            channel=notice.channel_id,
            ts=notice.message_ts,
            **msg,
        )

    def delete_notice_message(self, notice_id: str) -> bool:
        notice = self._store.get_notice(notice_id)
        if notice is None:
            return False
        if not notice.message_ts:
            return False
        self._client.chat_delete(channel=notice.channel_id, ts=notice.message_ts)
        self._store.update_message_ts(notice_id, "")
        return True

    def compute_response_rates(
        self,
        notices: list[Notice | MeetingNotice],
    ) -> dict[str, str]:
        channel_members: dict[str, list[str]] = {}
        rates: dict[str, str] = {}

        for notice in notices:
            if notice.channel_id not in channel_members:
                try:
                    channel_members[notice.channel_id] = self.get_channel_members(notice.channel_id)
                except SlackApiError:
                    logger.warning("channel_members_fetch_failed", channel_id=notice.channel_id)
                    channel_members[notice.channel_id] = []
            total = len(channel_members[notice.channel_id])
            if isinstance(notice, MeetingNotice):
                responded = len(notice.attendance)
            else:
                responded = len(notice.read_by)
            rates[notice.notice_id] = f"{responded}/{total}" if total > 0 else "-"

        return rates

    def mark_notice_read(self, notice_id: str, user_id: str) -> bool:
        notice = self._store.get_notice(notice_id)
        if notice is None:
            return False
        self._store.mark_read(notice_id, user_id)
        return True

    def set_meeting_attendance(self, notice_id: str, user_id: str, status: AttendanceStatus) -> bool:
        notice = self._store.get_notice(notice_id)
        if notice is None or not isinstance(notice, MeetingNotice):
            return False
        self._store.set_attendance(notice_id, user_id, status)
        return True

    def get_channel_members(self, channel_id: str) -> list[str]:
        channel_result = self._client.conversations_members(channel=channel_id)
        channel_ids = set(channel_result.get("members", []))
        if not channel_ids:
            return []

        users_result = self._client.users_list()
        return [
            u["id"]
            for u in users_result.get("members", [])
            if u["id"] in channel_ids and not u.get("is_bot") and u.get("id") != "USLACKBOT"
        ]

    def remind_unread_users(self, notice_id: str) -> int:
        notice = self._store.get_notice(notice_id)
        if notice is None:
            return 0

        members = self.get_channel_members(notice.channel_id)
        excludes = set(self._store.list_remind_excludes())
        unread = [m for m in members if not notice.is_read_by(m) and m not in excludes]

        link = _build_message_link(notice.channel_id, notice.message_ts)
        for user_id in unread:
            self._client.chat_postMessage(
                channel=user_id,
                text=(f"아직 확인하지 않은 공지가 있습니다: *{notice.title}*\n<{link}|공지 바로가기>"),
            )

        return len(unread)

    def remind_meeting_non_responders(self, notice_id: str) -> int:
        notice = self._store.get_notice(notice_id)
        if notice is None or not isinstance(notice, MeetingNotice):
            return 0

        members = self.get_channel_members(notice.channel_id)
        excludes = set(self._store.list_remind_excludes())
        non_responders = [m for m in members if m not in notice.attendance and m not in excludes]

        link = _build_message_link(notice.channel_id, notice.message_ts)
        for user_id in non_responders:
            self._client.chat_postMessage(
                channel=user_id,
                text=(f"아직 응답하지 않은 회의 공지가 있습니다: *{notice.title}*\n<{link}|공지 바로가기>"),
            )

        return len(non_responders)

from __future__ import annotations

import re

from slack_bolt import App
from slack_bolt.context.ack import Ack
from slack_sdk.web import WebClient

from src.events.home import _publish_home_tab
from src.services.notice_service import NoticeService
from src.store.models import AttendanceStatus, MeetingNotice
from src.store.notice_store import NoticeStore
from src.views.notice_views import (
    build_meeting_notice_edit_modal,
    build_meeting_notice_modal,
    build_meeting_status_modal,
    build_notice_create_modal,
    build_notice_delete_confirm_modal,
    build_notice_edit_modal,
    build_notice_status_modal,
    build_remind_exclude_modal,
)


def _send_feedback(client: WebClient, channel_id: str, user_id: str, text: str) -> None:
    if channel_id:
        client.chat_postEphemeral(channel=channel_id, user=user_id, text=text)
    else:
        client.chat_postMessage(channel=user_id, text=text)


USAGE_TEXT = (
    "*`/notice` 사용법:*\n"
    "• `/notice create` — 일반 공지 작성\n"
    "• `/notice meeting` — 회의 공지 작성"
)


def register_notice_commands(app: App, store: NoticeStore) -> None:
    @app.command("/notice")
    def handle_notice_command(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        text = str(body.get("text", "")).strip()
        trigger_id = str(body.get("trigger_id", ""))
        parts = text.split(maxsplit=1)
        subcommand = parts[0] if parts else ""

        if subcommand == "create":
            ack()
            channel_id = str(body.get("channel_id", ""))
            client.views_open(trigger_id=trigger_id, view=build_notice_create_modal(channel_id))

        elif subcommand == "meeting":
            ack()
            channel_id = str(body.get("channel_id", ""))
            client.views_open(trigger_id=trigger_id, view=build_meeting_notice_modal(channel_id))

        else:
            ack(text=USAGE_TEXT)

    @app.view("notice_create_modal")
    def handle_notice_create_submission(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
        view: dict[str, object],
    ) -> None:
        ack()
        state: dict[str, object] = view.get("state", {})  # type: ignore[assignment]
        values: dict[str, dict[str, dict[str, object]]] = state.get("values", {})  # type: ignore[assignment]
        title = str(values["title_block"]["title_input"].get("value", ""))
        content = str(values["content_block"]["content_input"].get("value", ""))
        channel_id = str(values["channel_block"]["channel_input"].get("selected_channel", ""))

        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        author_id = user.get("id", "")

        service = NoticeService(store, client)
        notice = service.create_and_post_notice(
            title=title,
            content=content,
            channel_id=channel_id,
            author_id=author_id,
        )

        client.chat_postMessage(
            channel=author_id,
            text=f"공지가 등록되었습니다: *{notice.title}* (ID: `{notice.notice_id}`)",
        )

    @app.view("meeting_notice_modal")
    def handle_meeting_notice_submission(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
        view: dict[str, object],
    ) -> None:
        ack()
        state: dict[str, object] = view.get("state", {})  # type: ignore[assignment]
        values: dict[str, dict[str, dict[str, object]]] = state.get("values", {})  # type: ignore[assignment]
        title = str(values["title_block"]["title_input"].get("value", ""))
        meeting_datetime = str(values["datetime_block"]["datetime_input"].get("selected_date_time", ""))
        location = str(values["location_block"]["location_input"].get("value", ""))
        agenda = str(values["agenda_block"]["agenda_input"].get("value", ""))
        channel_id = str(values["channel_block"]["channel_input"].get("selected_channel", ""))

        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        author_id = user.get("id", "")

        service = NoticeService(store, client)
        notice = service.create_and_post_meeting_notice(
            title=title,
            channel_id=channel_id,
            author_id=author_id,
            meeting_datetime=meeting_datetime,
            location=location,
            agenda=agenda,
        )

        client.chat_postMessage(
            channel=author_id,
            text=f"회의 공지가 등록되었습니다: *{notice.title}* (ID: `{notice.notice_id}`)",
        )

    @app.action(re.compile(r"^notice_confirm_(.+)$"))
    def handle_notice_confirm(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        actions: list[dict[str, str]] = body.get("actions", [])  # type: ignore[assignment]
        action_id = actions[0].get("action_id", "") if actions else ""
        match = re.match(r"^notice_confirm_(.+)$", action_id)
        if not match:
            return

        notice_id = match.group(1)
        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")
        channel: dict[str, str] = body.get("channel", {})  # type: ignore[assignment]
        channel_id = channel.get("id", "")

        service = NoticeService(store, client)
        service.mark_notice_read(notice_id, user_id)

        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="공지를 확인했습니다.",
        )

    @app.action(re.compile(r"^meeting_attend_(online|offline|absent)_(.+)$"))
    def handle_meeting_attendance(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        actions: list[dict[str, str]] = body.get("actions", [])  # type: ignore[assignment]
        action_id = actions[0].get("action_id", "") if actions else ""
        match = re.match(r"^meeting_attend_(online|offline|absent)_(.+)$", action_id)
        if not match:
            return

        status_str = match.group(1)
        notice_id = match.group(2)
        status = AttendanceStatus(status_str)

        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")
        channel: dict[str, str] = body.get("channel", {})  # type: ignore[assignment]
        channel_id = channel.get("id", "")

        service = NoticeService(store, client)
        service.set_meeting_attendance(notice_id, user_id, status)

        status_labels = {
            AttendanceStatus.ONLINE: "온라인 참석",
            AttendanceStatus.OFFLINE: "오프라인 참석",
            AttendanceStatus.ABSENT: "불참",
        }

        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"응답이 기록되었습니다: {status_labels[status]}",
        )

    @app.action(re.compile(r"^notice_status_(.+)$"))
    def handle_notice_status_button(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        actions: list[dict[str, str]] = body.get("actions", [])  # type: ignore[assignment]
        action_id = actions[0].get("action_id", "") if actions else ""
        match = re.match(r"^notice_status_(.+)$", action_id)
        if not match:
            return

        notice_id = match.group(1)
        trigger_id = str(body.get("trigger_id", ""))
        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")
        channel: dict[str, str] = body.get("channel") or {}  # type: ignore[assignment]
        channel_id = channel.get("id", "")

        notice = store.get_notice(notice_id)
        if notice is None:
            _send_feedback(client, channel_id, user_id, f"공지를 찾을 수 없습니다: `{notice_id}`")
            return

        service = NoticeService(store, client)
        members = service.get_channel_members(notice.channel_id)
        if isinstance(notice, MeetingNotice):
            modal = build_meeting_status_modal(notice, members)
        else:
            modal = build_notice_status_modal(notice, members)

        client.views_open(trigger_id=trigger_id, view=modal)

    @app.action(re.compile(r"^notice_remind_(.+)$"))
    def handle_notice_remind_button(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        actions: list[dict[str, str]] = body.get("actions", [])  # type: ignore[assignment]
        action_id = actions[0].get("action_id", "") if actions else ""
        match = re.match(r"^notice_remind_(.+)$", action_id)
        if not match:
            return

        notice_id = match.group(1)
        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")
        channel: dict[str, str] = body.get("channel") or {}  # type: ignore[assignment]
        channel_id = channel.get("id", "")

        notice = store.get_notice(notice_id)
        if notice is None:
            _send_feedback(client, channel_id, user_id, f"공지를 찾을 수 없습니다: `{notice_id}`")
            return

        service = NoticeService(store, client)
        if isinstance(notice, MeetingNotice):
            count = service.remind_meeting_non_responders(notice.notice_id)
            _send_feedback(client, channel_id, user_id, f"{count}명에게 참석 여부 리마인드를 보냈습니다.")
        else:
            count = service.remind_unread_users(notice.notice_id)
            _send_feedback(client, channel_id, user_id, f"{count}명에게 읽음 확인 리마인드를 보냈습니다.")

    @app.action(re.compile(r"^notice_edit_(.+)$"))
    def handle_notice_edit_button(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        actions: list[dict[str, str]] = body.get("actions", [])  # type: ignore[assignment]
        action_id = actions[0].get("action_id", "") if actions else ""
        match = re.match(r"^notice_edit_(.+)$", action_id)
        if not match:
            return

        notice_id = match.group(1)
        trigger_id = str(body.get("trigger_id", ""))
        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")
        channel: dict[str, str] = body.get("channel") or {}  # type: ignore[assignment]
        channel_id = channel.get("id", "")

        notice = store.get_notice(notice_id)
        if notice is None:
            _send_feedback(client, channel_id, user_id, f"공지를 찾을 수 없습니다: `{notice_id}`")
            return

        if notice.author_id != user_id:
            _send_feedback(client, channel_id, user_id, "작성자만 공지를 수정할 수 있습니다.")
            return

        if isinstance(notice, MeetingNotice):
            modal = build_meeting_notice_edit_modal(notice)
        else:
            modal = build_notice_edit_modal(notice)

        client.views_open(trigger_id=trigger_id, view=modal)

    @app.view("notice_edit_modal")
    def handle_notice_edit_submission(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
        view: dict[str, object],
    ) -> None:
        ack()
        private_metadata = str(view.get("private_metadata", ""))
        state: dict[str, object] = view.get("state", {})  # type: ignore[assignment]
        values: dict[str, dict[str, dict[str, object]]] = state.get("values", {})  # type: ignore[assignment]
        title = str(values["title_block"]["title_input"].get("value", ""))
        content = str(values["content_block"]["content_input"].get("value", ""))

        service = NoticeService(store, client)
        service.update_and_repost_notice(private_metadata, title, content)

    @app.view("meeting_notice_edit_modal")
    def handle_meeting_notice_edit_submission(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
        view: dict[str, object],
    ) -> None:
        ack()
        private_metadata = str(view.get("private_metadata", ""))
        state: dict[str, object] = view.get("state", {})  # type: ignore[assignment]
        values: dict[str, dict[str, dict[str, object]]] = state.get("values", {})  # type: ignore[assignment]
        title = str(values["title_block"]["title_input"].get("value", ""))
        meeting_datetime = str(values["datetime_block"]["datetime_input"].get("selected_date_time", ""))
        location = str(values["location_block"]["location_input"].get("value", ""))
        agenda = str(values["agenda_block"]["agenda_input"].get("value", ""))

        service = NoticeService(store, client)
        service.update_and_repost_meeting_notice(private_metadata, title, meeting_datetime, location, agenda)

    @app.action(re.compile(r"^notice_delete_(.+)$"))
    def handle_notice_delete_button(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        actions: list[dict[str, str]] = body.get("actions", [])  # type: ignore[assignment]
        action_id = actions[0].get("action_id", "") if actions else ""
        match = re.match(r"^notice_delete_(.+)$", action_id)
        if not match:
            return

        notice_id = match.group(1)
        trigger_id = str(body.get("trigger_id", ""))
        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")
        channel: dict[str, str] = body.get("channel") or {}  # type: ignore[assignment]
        channel_id = channel.get("id", "")

        notice = store.get_notice(notice_id)
        if notice is None:
            _send_feedback(client, channel_id, user_id, f"공지를 찾을 수 없습니다: `{notice_id}`")
            return

        if notice.author_id != user_id:
            _send_feedback(client, channel_id, user_id, "작성자만 공지를 삭제할 수 있습니다.")
            return

        modal = build_notice_delete_confirm_modal(notice)
        client.views_open(trigger_id=trigger_id, view=modal)

    @app.view("notice_delete_confirm")
    def handle_notice_delete_confirm(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
        view: dict[str, object],
    ) -> None:
        ack()
        notice_id = str(view.get("private_metadata", ""))
        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")

        service = NoticeService(store, client)
        service.delete_notice_message(notice_id)

        client.chat_postMessage(
            channel=user_id,
            text=f"공지 메시지가 삭제되었습니다. (ID: `{notice_id}`)",
        )

        _publish_home_tab(client, user_id, store)

    @app.action("remind_exclude_manage")
    def handle_remind_exclude_manage(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        trigger_id = str(body.get("trigger_id", ""))
        excludes = store.list_remind_excludes()
        modal = build_remind_exclude_modal(excludes)
        client.views_open(trigger_id=trigger_id, view=modal)

    @app.view("remind_exclude_modal")
    def handle_remind_exclude_submission(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
        view: dict[str, object],
    ) -> None:
        ack()
        state: dict[str, object] = view.get("state", {})  # type: ignore[assignment]
        values: dict[str, dict[str, dict[str, object]]] = state.get("values", {})  # type: ignore[assignment]
        selected: list[str] = values["exclude_block"]["remind_exclude_users"].get("selected_users", [])  # type: ignore[assignment]

        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")

        current = set(store.list_remind_excludes())
        new_set = set(selected)

        for uid in new_set - current:
            store.add_remind_exclude(uid)
        for uid in current - new_set:
            store.remove_remind_exclude(uid)

        client.chat_postMessage(
            channel=user_id,
            text=f"리마인드 예외 목록이 업데이트되었습니다. ({len(new_set)}명)",
        )

        _publish_home_tab(client, user_id, store)

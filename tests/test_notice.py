from __future__ import annotations

import json
import time
from unittest.mock import patch

from slack_bolt import App, BoltRequest
from slack_sdk.web import SlackResponse

from src.app import create_app
from src.config import Settings
from src.services.notice_service import _build_message_link
from src.store.models import AttendanceStatus, MeetingNotice, Notice, NoticeType, generate_notice_id
from src.store.notice_store import NoticeStore
from src.views.notice_views import (
    build_home_tab_view,
    build_meeting_notice_edit_modal,
    build_meeting_notice_message,
    build_meeting_notice_modal,
    build_meeting_status_message,
    build_meeting_status_modal,
    build_notice_create_modal,
    build_notice_dashboard_modal,
    build_notice_delete_confirm_modal,
    build_notice_edit_modal,
    build_notice_list_message,
    build_notice_message,
    build_notice_status_message,
    build_notice_status_modal,
    build_remind_exclude_modal,
)

_MOCK_AUTH_RESPONSE = SlackResponse(
    client=None,  # type: ignore[arg-type]
    http_verb="POST",
    api_url="https://slack.com/api/auth.test",
    req_args={},
    data={"ok": True, "user_id": "U1234", "bot_id": "B1234", "team_id": "T1234"},
    headers={},
    status_code=200,
)


def _make_settings() -> Settings:
    return Settings(
        slack_bot_token="xoxb-test",
        slack_app_token="xapp-test",
        slack_signing_secret="test-secret",
    )


def _create_test_app(store: NoticeStore | None = None) -> App:
    if store is None:
        store = NoticeStore()
    with patch("slack_sdk.web.client.WebClient.auth_test", return_value=_MOCK_AUTH_RESPONSE):
        return create_app(
            _make_settings(),
            request_verification_enabled=False,
            notice_store=store,
        )


def _make_notice(notice_id: str = "notice_123_abcd", **kwargs: object) -> Notice:
    defaults: dict[str, object] = {
        "notice_id": notice_id,
        "notice_type": NoticeType.GENERAL,
        "title": "테스트 공지",
        "content": "테스트 내용입니다.",
        "channel_id": "C1234",
        "author_id": "U1234",
        "created_at": 1707350400.0,
        "message_ts": "1707350400.000001",
    }
    defaults.update(kwargs)
    return Notice(**defaults)  # type: ignore[arg-type]


def _make_meeting_notice(notice_id: str = "notice_123_meet", **kwargs: object) -> MeetingNotice:
    defaults: dict[str, object] = {
        "notice_id": notice_id,
        "notice_type": NoticeType.MEETING,
        "title": "테스트 회의",
        "content": "회의: 테스트 회의",
        "channel_id": "C1234",
        "author_id": "U1234",
        "created_at": 1707350400.0,
        "message_ts": "1707350400.000002",
        "meeting_datetime": "1707440000",
        "location": "회의실 A",
        "agenda": "안건 1\n안건 2",
    }
    defaults.update(kwargs)
    return MeetingNotice(**defaults)  # type: ignore[arg-type]


class TestNoticeModels:
    def test_generate_notice_id(self) -> None:
        nid = generate_notice_id()
        assert nid.startswith("notice_")
        parts = nid.split("_")
        assert len(parts) == 3

    def test_notice_mark_read(self) -> None:
        notice = _make_notice()
        assert not notice.is_read_by("U999")
        notice.mark_read("U999")
        assert notice.is_read_by("U999")
        notice.mark_read("U999")
        assert notice.read_by.count("U999") == 1

    def test_meeting_notice_attendance(self) -> None:
        notice = _make_meeting_notice()
        assert notice.get_attendance("U999") is None
        notice.set_attendance("U999", AttendanceStatus.ONLINE)
        assert notice.get_attendance("U999") == AttendanceStatus.ONLINE
        notice.set_attendance("U999", AttendanceStatus.ABSENT)
        assert notice.get_attendance("U999") == AttendanceStatus.ABSENT


class TestNoticeStore:
    def test_create_and_get_notice(self) -> None:
        store = NoticeStore()
        notice = _make_notice()
        store.create_notice(notice)

        retrieved = store.get_notice(notice.notice_id)
        assert retrieved is not None
        assert retrieved.title == "테스트 공지"
        assert retrieved.notice_type == NoticeType.GENERAL
        store.close()

    def test_create_and_get_meeting_notice(self) -> None:
        store = NoticeStore()
        notice = _make_meeting_notice()
        store.create_meeting_notice(notice)

        retrieved = store.get_notice(notice.notice_id)
        assert retrieved is not None
        assert isinstance(retrieved, MeetingNotice)
        assert retrieved.location == "회의실 A"
        assert retrieved.meeting_datetime == "1707440000"
        store.close()

    def test_get_nonexistent_notice(self) -> None:
        store = NoticeStore()
        assert store.get_notice("nonexistent") is None
        store.close()

    def test_mark_read(self) -> None:
        store = NoticeStore()
        notice = _make_notice()
        store.create_notice(notice)
        store.mark_read(notice.notice_id, "U999")

        retrieved = store.get_notice(notice.notice_id)
        assert retrieved is not None
        assert retrieved.is_read_by("U999")
        store.close()

    def test_set_attendance(self) -> None:
        store = NoticeStore()
        notice = _make_meeting_notice()
        store.create_meeting_notice(notice)
        store.set_attendance(notice.notice_id, "U999", AttendanceStatus.OFFLINE)

        retrieved = store.get_notice(notice.notice_id)
        assert isinstance(retrieved, MeetingNotice)
        assert retrieved.get_attendance("U999") == AttendanceStatus.OFFLINE
        store.close()

    def test_list_notices(self) -> None:
        store = NoticeStore()
        n1 = _make_notice("notice_001_aaaa")
        n2 = _make_meeting_notice("notice_002_bbbb")
        store.create_notice(n1)
        store.create_meeting_notice(n2)

        notices = store.list_notices()
        assert len(notices) == 2
        store.close()

    def test_list_notices_by_channel(self) -> None:
        store = NoticeStore()
        n1 = _make_notice("notice_001_aaaa", channel_id="C1111")
        n2 = _make_notice("notice_002_bbbb", channel_id="C2222")
        store.create_notice(n1)
        store.create_notice(n2)

        notices = store.list_notices(channel_id="C1111")
        assert len(notices) == 1
        assert notices[0].channel_id == "C1111"
        store.close()

    def test_update_message_ts(self) -> None:
        store = NoticeStore()
        notice = _make_notice(message_ts="")
        store.create_notice(notice)
        store.update_message_ts(notice.notice_id, "1707350400.999")

        retrieved = store.get_notice(notice.notice_id)
        assert retrieved is not None
        assert retrieved.message_ts == "1707350400.999"
        store.close()


class TestNoticeViews:
    def test_build_notice_create_modal(self) -> None:
        modal = build_notice_create_modal()
        assert modal["type"] == "modal"
        assert modal["callback_id"] == "notice_create_modal"
        assert len(modal["blocks"]) == 3
        block_ids = [b["block_id"] for b in modal["blocks"]]
        assert "title_block" in block_ids
        assert "content_block" in block_ids
        assert "channel_block" in block_ids
        channel_el = modal["blocks"][2]["element"]
        assert "initial_channel" not in channel_el

    def test_build_notice_create_modal_with_channel(self) -> None:
        modal = build_notice_create_modal(channel_id="C_TEST")
        channel_el = modal["blocks"][2]["element"]
        assert channel_el["initial_channel"] == "C_TEST"

    def test_build_meeting_notice_modal(self) -> None:
        modal = build_meeting_notice_modal()
        assert modal["type"] == "modal"
        assert modal["callback_id"] == "meeting_notice_modal"
        assert len(modal["blocks"]) == 5
        block_ids = [b["block_id"] for b in modal["blocks"]]
        assert "datetime_block" in block_ids
        assert "location_block" in block_ids
        assert "agenda_block" in block_ids
        channel_el = modal["blocks"][4]["element"]
        assert "initial_channel" not in channel_el

    def test_build_meeting_notice_modal_with_channel(self) -> None:
        modal = build_meeting_notice_modal(channel_id="C_TEST")
        channel_el = modal["blocks"][4]["element"]
        assert channel_el["initial_channel"] == "C_TEST"

    def test_build_notice_message(self) -> None:
        notice = _make_notice()
        msg = build_notice_message(notice)
        assert "[공지]" in msg["text"]
        actions_block = [b for b in msg["blocks"] if b["type"] == "actions"][0]
        btn = actions_block["elements"][0]
        assert btn["action_id"] == f"notice_confirm_{notice.notice_id}"

    def test_build_notice_message_has_confirm_and_status_buttons(self) -> None:
        notice = _make_notice()
        msg = build_notice_message(notice)
        actions_block = [b for b in msg["blocks"] if b["type"] == "actions"][0]
        action_ids = [e["action_id"] for e in actions_block["elements"]]
        assert len(action_ids) == 2
        assert f"notice_confirm_{notice.notice_id}" in action_ids
        assert f"notice_status_{notice.notice_id}" in action_ids
        assert f"notice_remind_{notice.notice_id}" not in action_ids
        assert f"notice_edit_{notice.notice_id}" not in action_ids

    def test_build_meeting_notice_message(self) -> None:
        notice = _make_meeting_notice()
        msg = build_meeting_notice_message(notice)
        assert "[회의 공지]" in msg["text"]
        actions_block = [b for b in msg["blocks"] if b["type"] == "actions"][0]
        action_ids = [e["action_id"] for e in actions_block["elements"]]
        assert any("meeting_attend_online_" in a for a in action_ids)
        assert any("meeting_attend_offline_" in a for a in action_ids)
        assert any("meeting_attend_absent_" in a for a in action_ids)

    def test_build_meeting_notice_message_has_status_but_no_remind_edit(self) -> None:
        notice = _make_meeting_notice()
        msg = build_meeting_notice_message(notice)
        actions_block = [b for b in msg["blocks"] if b["type"] == "actions"][0]
        action_ids = [e["action_id"] for e in actions_block["elements"]]
        assert len(action_ids) == 4
        assert f"notice_status_{notice.notice_id}" in action_ids
        assert not any("notice_remind_" in a for a in action_ids)
        assert not any("notice_edit_" in a for a in action_ids)

    def test_build_notice_list_message_empty(self) -> None:
        msg = build_notice_list_message([])
        assert "없습니다" in msg["text"]

    def test_build_notice_list_message(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice(), _make_meeting_notice()]
        msg = build_notice_list_message(notices)
        assert "공지 목록" in msg["text"]
        section_blocks = [b for b in msg["blocks"] if b["type"] == "section"]
        assert len(section_blocks) == 2

    def test_build_notice_status_message(self) -> None:
        notice = _make_notice()
        notice.mark_read("U001")
        msg = build_notice_status_message(notice, ["U001", "U002"])
        # header + divider + content section + context + divider + status section = 6 blocks
        assert len(msg["blocks"]) == 6
        # Content section shows the notice content
        content_section = msg["blocks"][2]
        assert notice.content in content_section["text"]["text"]
        # Status section shows read/unread
        status_section = msg["blocks"][5]
        assert "확인 (1명)" in status_section["text"]["text"]
        assert "미확인 (1명)" in status_section["text"]["text"]

    def test_build_meeting_status_message(self) -> None:
        notice = _make_meeting_notice()
        notice.set_attendance("U001", AttendanceStatus.ONLINE)
        notice.set_attendance("U002", AttendanceStatus.ABSENT)
        msg = build_meeting_status_message(notice, ["U001", "U002", "U003"])
        # header + divider + datetime/location + agenda + context + divider + status = 7 blocks
        assert len(msg["blocks"]) == 7
        # Meeting details are shown
        fields_section = msg["blocks"][2]
        field_texts = [f["text"] for f in fields_section["fields"]]
        assert any("일시" in t for t in field_texts)
        assert any("장소" in t for t in field_texts)
        agenda_section = msg["blocks"][3]
        assert "안건" in agenda_section["text"]["text"]
        # Status section shows attendance
        status_section = msg["blocks"][6]
        assert "온라인 (1명)" in status_section["text"]["text"]
        assert "불참 (1명)" in status_section["text"]["text"]
        assert "미응답 (1명)" in status_section["text"]["text"]


class TestNoticeCommands:
    def test_notice_no_subcommand_shows_usage(self) -> None:
        app = _create_test_app()
        request = BoltRequest(
            body="command=%2Fnotice&text=&user_id=U1234&trigger_id=T123&channel_id=C1234",
            headers={"content-type": ["application/x-www-form-urlencoded"]},
        )
        response = app.dispatch(request)
        assert response.status == 200
        assert "사용법" in (response.body or "")

    def test_notice_create_opens_modal(self) -> None:
        app = _create_test_app()
        with patch("slack_sdk.web.client.WebClient.views_open") as mock_views_open:
            request = BoltRequest(
                body="command=%2Fnotice&text=create&user_id=U1234&trigger_id=T123&channel_id=C1234",
                headers={"content-type": ["application/x-www-form-urlencoded"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            mock_views_open.assert_called_once()
            call_kwargs = mock_views_open.call_args
            view = call_kwargs.kwargs.get("view") or call_kwargs[1].get("view")
            assert view["callback_id"] == "notice_create_modal"

    def test_notice_meeting_opens_modal(self) -> None:
        app = _create_test_app()
        with patch("slack_sdk.web.client.WebClient.views_open") as mock_views_open:
            request = BoltRequest(
                body="command=%2Fnotice&text=meeting&user_id=U1234&trigger_id=T123&channel_id=C1234",
                headers={"content-type": ["application/x-www-form-urlencoded"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            mock_views_open.assert_called_once()
            call_kwargs = mock_views_open.call_args
            view = call_kwargs.kwargs.get("view") or call_kwargs[1].get("view")
            assert view["callback_id"] == "meeting_notice_modal"


class TestNoticeActions:
    def test_notice_confirm_button(self) -> None:
        store = NoticeStore()
        notice = _make_notice()
        store.create_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "channel": {"id": "C1234"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"notice_confirm_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.chat_postEphemeral"):
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            # Action listeners run asynchronously; wait for completion
            time.sleep(0.5)

        retrieved = store.get_notice(notice.notice_id)
        assert retrieved is not None
        assert retrieved.is_read_by("U999")

    def test_meeting_attend_button(self) -> None:
        store = NoticeStore()
        notice = _make_meeting_notice()
        store.create_meeting_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "channel": {"id": "C1234"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"meeting_attend_online_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.chat_postEphemeral"):
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)

        retrieved = store.get_notice(notice.notice_id)
        assert isinstance(retrieved, MeetingNotice)
        assert retrieved.get_attendance("U999") == AttendanceStatus.ONLINE

    def test_meeting_attend_absent_button(self) -> None:
        store = NoticeStore()
        notice = _make_meeting_notice()
        store.create_meeting_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "channel": {"id": "C1234"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"meeting_attend_absent_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.chat_postEphemeral"):
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)

        retrieved = store.get_notice(notice.notice_id)
        assert isinstance(retrieved, MeetingNotice)
        assert retrieved.get_attendance("U999") == AttendanceStatus.ABSENT

    def test_notice_status_button(self) -> None:
        store = NoticeStore()
        notice = _make_notice()
        store.create_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "channel": {"id": "C1234"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"notice_status_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with (
            patch("slack_sdk.web.client.WebClient.conversations_members") as mock_members,
            patch("slack_sdk.web.client.WebClient.views_open") as mock_views_open,
        ):
            mock_members.return_value = {"members": ["U001", "U002"]}
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_views_open.assert_called_once()
            call_kwargs = mock_views_open.call_args.kwargs
            view = call_kwargs.get("view", {})
            assert view["type"] == "modal"
            assert view["title"]["text"] == "읽음 현황"

    def test_notice_status_button_meeting(self) -> None:
        store = NoticeStore()
        notice = _make_meeting_notice()
        store.create_meeting_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "channel": {"id": "C1234"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"notice_status_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with (
            patch("slack_sdk.web.client.WebClient.conversations_members") as mock_members,
            patch("slack_sdk.web.client.WebClient.views_open") as mock_views_open,
        ):
            mock_members.return_value = {"members": ["U001", "U002"]}
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_views_open.assert_called_once()
            call_kwargs = mock_views_open.call_args.kwargs
            view = call_kwargs.get("view", {})
            assert view["type"] == "modal"
            assert view["title"]["text"] == "참석 현황"

    def test_notice_remind_button(self) -> None:
        store = NoticeStore()
        notice = _make_notice()
        store.create_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "channel": {"id": "C1234"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"notice_remind_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with (
            patch("slack_sdk.web.client.WebClient.conversations_members") as mock_members,
            patch("slack_sdk.web.client.WebClient.chat_postMessage") as mock_post,
            patch("slack_sdk.web.client.WebClient.chat_postEphemeral") as mock_ephemeral,
        ):
            mock_members.return_value = {"members": ["U001", "U002"]}
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            assert mock_post.call_count == 2
            mock_ephemeral.assert_called_once()
            call_kwargs = mock_ephemeral.call_args.kwargs
            assert "2명에게 읽음 확인 리마인드" in call_kwargs.get("text", "")

    def test_notice_status_button_not_found(self) -> None:
        app = _create_test_app()

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "channel": {"id": "C1234"},
            "actions": [
                {
                    "type": "button",
                    "action_id": "notice_status_nonexistent",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.chat_postEphemeral") as mock_ephemeral:
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_ephemeral.assert_called_once()
            call_kwargs = mock_ephemeral.call_args.kwargs
            assert "찾을 수 없습니다" in call_kwargs.get("text", "")


class TestNoticeMessageButtons:
    def test_notice_message_has_confirm_and_status_buttons(self) -> None:
        notice = _make_notice()
        msg = build_notice_message(notice)
        actions_block = [b for b in msg["blocks"] if b["type"] == "actions"][0]
        action_ids = [e["action_id"] for e in actions_block["elements"]]
        assert f"notice_confirm_{notice.notice_id}" in action_ids
        assert f"notice_status_{notice.notice_id}" in action_ids
        assert f"notice_remind_{notice.notice_id}" not in action_ids
        assert f"notice_edit_{notice.notice_id}" not in action_ids

    def test_meeting_message_has_attendance_and_status_buttons(self) -> None:
        notice = _make_meeting_notice()
        msg = build_meeting_notice_message(notice)
        actions_block = [b for b in msg["blocks"] if b["type"] == "actions"][0]
        action_ids = [e["action_id"] for e in actions_block["elements"]]
        assert any("meeting_attend_online_" in a for a in action_ids)
        assert any("meeting_attend_offline_" in a for a in action_ids)
        assert any("meeting_attend_absent_" in a for a in action_ids)
        assert f"notice_status_{notice.notice_id}" in action_ids
        assert f"notice_remind_{notice.notice_id}" not in action_ids
        assert f"notice_edit_{notice.notice_id}" not in action_ids


class TestMessageLink:
    def test_build_message_link(self) -> None:
        link = _build_message_link("C1234", "1707350400.000001")
        assert link == "https://slack.com/archives/C1234/p1707350400000001"


class TestNoticeDashboard:
    def test_build_dashboard_modal_empty(self) -> None:
        modal = build_notice_dashboard_modal([])
        assert modal["type"] == "modal"
        assert modal["callback_id"] == "notice_dashboard_modal"
        assert len(modal["blocks"]) == 1
        assert "없습니다" in modal["blocks"][0]["text"]["text"]

    def test_build_dashboard_modal_with_notices(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice(), _make_meeting_notice()]
        modal = build_notice_dashboard_modal(notices)
        # Each notice: section + actions + divider = 3 blocks, 2 notices = 6
        assert len(modal["blocks"]) == 6
        texts = [b["text"]["text"] for b in modal["blocks"] if b["type"] == "section"]
        assert any("일반" in t for t in texts)
        assert any("회의" in t for t in texts)
        assert any("응답률: -" in t for t in texts)

    def test_dashboard_blocks_author_sees_all_buttons(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice(author_id="U1234")]
        modal = build_notice_dashboard_modal(notices, viewer_id="U1234")
        actions_blocks = [b for b in modal["blocks"] if b["type"] == "actions"]
        assert len(actions_blocks) == 1
        action_ids = [e["action_id"] for e in actions_blocks[0]["elements"]]
        notice_id = notices[0].notice_id
        assert f"notice_status_{notice_id}" in action_ids
        assert f"notice_remind_{notice_id}" in action_ids
        assert f"notice_edit_{notice_id}" in action_ids
        assert f"notice_delete_{notice_id}" in action_ids
        assert len(action_ids) == 4

    def test_dashboard_blocks_non_author_sees_limited_buttons(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice(author_id="U_AUTHOR")]
        modal = build_notice_dashboard_modal(notices, viewer_id="U_OTHER")
        actions_blocks = [b for b in modal["blocks"] if b["type"] == "actions"]
        assert len(actions_blocks) == 1
        action_ids = [e["action_id"] for e in actions_blocks[0]["elements"]]
        notice_id = notices[0].notice_id
        assert f"notice_status_{notice_id}" in action_ids
        assert f"notice_remind_{notice_id}" not in action_ids
        assert f"notice_edit_{notice_id}" not in action_ids
        assert f"notice_delete_{notice_id}" not in action_ids
        assert len(action_ids) == 1


class TestStoreUpdate:
    def test_update_notice(self) -> None:
        store = NoticeStore()
        notice = _make_notice()
        store.create_notice(notice)
        store.update_notice(notice.notice_id, "수정된 제목", "수정된 내용")

        retrieved = store.get_notice(notice.notice_id)
        assert retrieved is not None
        assert retrieved.title == "수정된 제목"
        assert retrieved.content == "수정된 내용"
        store.close()

    def test_update_meeting_notice(self) -> None:
        store = NoticeStore()
        notice = _make_meeting_notice()
        store.create_meeting_notice(notice)
        store.update_meeting_notice(notice.notice_id, "수정된 회의", "1707500000", "회의실 B", "새 안건")

        retrieved = store.get_notice(notice.notice_id)
        assert isinstance(retrieved, MeetingNotice)
        assert retrieved.title == "수정된 회의"
        assert retrieved.meeting_datetime == "1707500000"
        assert retrieved.location == "회의실 B"
        assert retrieved.agenda == "새 안건"
        store.close()


class TestNoticeEditViews:
    def test_build_notice_edit_modal(self) -> None:
        notice = _make_notice()
        modal = build_notice_edit_modal(notice)
        assert modal["type"] == "modal"
        assert modal["callback_id"] == "notice_edit_modal"
        assert modal["private_metadata"] == notice.notice_id
        title_block = modal["blocks"][0]
        assert title_block["element"]["initial_value"] == notice.title
        content_block = modal["blocks"][1]
        assert content_block["element"]["initial_value"] == notice.content

    def test_build_meeting_notice_edit_modal(self) -> None:
        notice = _make_meeting_notice()
        modal = build_meeting_notice_edit_modal(notice)
        assert modal["type"] == "modal"
        assert modal["callback_id"] == "meeting_notice_edit_modal"
        assert modal["private_metadata"] == notice.notice_id
        assert len(modal["blocks"]) == 4

    def test_build_notice_status_modal(self) -> None:
        notice = _make_notice()
        notice.mark_read("U001")
        modal = build_notice_status_modal(notice, ["U001", "U002"])
        assert modal["type"] == "modal"
        assert modal["title"]["text"] == "읽음 현황"
        assert "submit" not in modal

    def test_build_meeting_status_modal(self) -> None:
        notice = _make_meeting_notice()
        notice.set_attendance("U001", AttendanceStatus.ONLINE)
        modal = build_meeting_status_modal(notice, ["U001", "U002"])
        assert modal["type"] == "modal"
        assert modal["title"]["text"] == "참석 현황"
        assert "submit" not in modal


class TestHomeTabView:
    def test_build_home_tab_view_empty(self) -> None:
        view = build_home_tab_view([])
        assert view["type"] == "home"
        assert any(b.get("type") == "header" for b in view["blocks"])
        texts = " ".join(b.get("text", {}).get("text", "") for b in view["blocks"] if b["type"] == "section")
        assert "없습니다" in texts

    def test_build_home_tab_view_with_notices(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice(), _make_meeting_notice()]
        view = build_home_tab_view(notices, total_count=2)
        assert view["type"] == "home"
        section_blocks = [b for b in view["blocks"] if b["type"] == "section"]
        assert len(section_blocks) == 2
        actions_blocks = [b for b in view["blocks"] if b["type"] == "actions"]
        # 1 top bar (create + exclude) + 2 notice actions = 3
        assert len(actions_blocks) == 3
        # First actions block should have create buttons and exclude manage
        first_actions = actions_blocks[0]
        assert any(e["action_id"] == "home_notice_create" for e in first_actions["elements"])
        assert any(e["action_id"] == "home_meeting_notice_create" for e in first_actions["elements"])
        assert any(e["action_id"] == "remind_exclude_manage" for e in first_actions["elements"])

    def test_build_home_tab_view_block_structure(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice()]
        view = build_home_tab_view(notices, total_count=1)
        # header + top_actions + divider + (section + actions + divider) = 6
        assert len(view["blocks"]) == 6


class TestNoticeEditActions:
    def test_notice_edit_button_non_author(self) -> None:
        store = NoticeStore()
        notice = _make_notice(author_id="U_AUTHOR")
        store.create_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U_OTHER"},
            "channel": {"id": "C1234"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"notice_edit_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.chat_postEphemeral") as mock_ephemeral:
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_ephemeral.assert_called_once()
            call_kwargs = mock_ephemeral.call_args.kwargs
            assert "작성자만" in call_kwargs.get("text", "")

    def test_notice_edit_button_author(self) -> None:
        store = NoticeStore()
        notice = _make_notice(author_id="U_AUTHOR")
        store.create_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U_AUTHOR"},
            "channel": {"id": "C1234"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"notice_edit_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.views_open") as mock_views_open:
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_views_open.assert_called_once()
            call_kwargs = mock_views_open.call_args.kwargs
            view = call_kwargs.get("view", {})
            assert view["callback_id"] == "notice_edit_modal"

    def test_meeting_edit_button_author(self) -> None:
        store = NoticeStore()
        notice = _make_meeting_notice(author_id="U_AUTHOR")
        store.create_meeting_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U_AUTHOR"},
            "channel": {"id": "C1234"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"notice_edit_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.views_open") as mock_views_open:
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_views_open.assert_called_once()
            call_kwargs = mock_views_open.call_args.kwargs
            view = call_kwargs.get("view", {})
            assert view["callback_id"] == "meeting_notice_edit_modal"


class TestAppHomeOpened:
    def test_app_home_opened_publishes_view(self) -> None:
        store = NoticeStore()
        notice = _make_notice()
        store.create_notice(notice)
        app = _create_test_app(store)

        event_payload = {
            "type": "event_callback",
            "event": {
                "type": "app_home_opened",
                "user": "U9999",
                "tab": "home",
                "channel": "C1234",
            },
            "token": "test-token",
            "team_id": "T1234",
            "event_id": "Ev1234",
            "event_time": 1707350400,
        }

        with (
            patch("slack_sdk.web.client.WebClient.conversations_members") as mock_members,
            patch("slack_sdk.web.client.WebClient.views_publish") as mock_publish,
        ):
            mock_members.return_value = {"members": ["U001", "U002"]}
            request = BoltRequest(
                body=json.dumps(event_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_publish.assert_called_once()
            call_kwargs = mock_publish.call_args.kwargs
            view = call_kwargs.get("view", {})
            assert view["type"] == "home"

    def test_app_home_opened_messages_tab_ignored(self) -> None:
        app = _create_test_app()

        event_payload = {
            "type": "event_callback",
            "event": {
                "type": "app_home_opened",
                "user": "U9999",
                "tab": "messages",
                "channel": "C1234",
            },
            "token": "test-token",
            "team_id": "T1234",
            "event_id": "Ev1234",
            "event_time": 1707350400,
        }

        with patch("slack_sdk.web.client.WebClient.views_publish") as mock_publish:
            request = BoltRequest(
                body=json.dumps(event_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_publish.assert_not_called()


class TestHomeTabButtonActions:
    """Test button actions triggered from Home Tab (no channel in body)."""

    def test_status_button_from_home_tab(self) -> None:
        store = NoticeStore()
        notice = _make_notice()
        store.create_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"notice_status_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with (
            patch("slack_sdk.web.client.WebClient.conversations_members") as mock_members,
            patch("slack_sdk.web.client.WebClient.views_open") as mock_views_open,
        ):
            mock_members.return_value = {"members": ["U001", "U002"]}
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_views_open.assert_called_once()

    def test_remind_button_from_home_tab_sends_dm(self) -> None:
        store = NoticeStore()
        notice = _make_notice()
        store.create_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"notice_remind_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with (
            patch("slack_sdk.web.client.WebClient.conversations_members") as mock_members,
            patch("slack_sdk.web.client.WebClient.chat_postMessage") as mock_post,
        ):
            mock_members.return_value = {"members": ["U001", "U002"]}
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            # 2 remind DMs + 1 feedback DM to user
            assert mock_post.call_count == 3
            feedback_call = mock_post.call_args_list[-1]
            assert feedback_call.kwargs.get("channel") == "U999"
            assert "리마인드" in feedback_call.kwargs.get("text", "")

    def test_edit_button_from_home_tab_non_author_sends_dm(self) -> None:
        store = NoticeStore()
        notice = _make_notice(author_id="U_AUTHOR")
        store.create_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U_OTHER"},
            "actions": [
                {
                    "type": "button",
                    "action_id": f"notice_edit_{notice.notice_id}",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.chat_postMessage") as mock_post:
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs.get("channel") == "U_OTHER"
            assert "작성자만" in call_kwargs.get("text", "")

    def test_status_not_found_from_home_tab_sends_dm(self) -> None:
        app = _create_test_app()

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "actions": [
                {
                    "type": "button",
                    "action_id": "notice_status_nonexistent",
                }
            ],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.chat_postMessage") as mock_post:
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs.get("channel") == "U999"
            assert "찾을 수 없습니다" in call_kwargs.get("text", "")


class TestStoreOffset:
    def test_list_notices_with_offset(self) -> None:
        store = NoticeStore()
        for i in range(7):
            n = _make_notice(f"notice_{i:03d}_aaaa", created_at=1707350400.0 + i)
            store.create_notice(n)

        page1 = store.list_notices(limit=5, offset=0)
        assert len(page1) == 5

        page2 = store.list_notices(limit=5, offset=5)
        assert len(page2) == 2

        ids_p1 = {n.notice_id for n in page1}
        ids_p2 = {n.notice_id for n in page2}
        assert ids_p1.isdisjoint(ids_p2)
        store.close()

    def test_count_notices(self) -> None:
        store = NoticeStore()
        assert store.count_notices() == 0
        for i in range(3):
            store.create_notice(_make_notice(f"notice_{i:03d}_aaaa"))
        assert store.count_notices() == 3
        store.close()

    def test_count_notices_by_channel(self) -> None:
        store = NoticeStore()
        store.create_notice(_make_notice("notice_001_aaaa", channel_id="C1111"))
        store.create_notice(_make_notice("notice_002_bbbb", channel_id="C1111"))
        store.create_notice(_make_notice("notice_003_cccc", channel_id="C2222"))
        assert store.count_notices(channel_id="C1111") == 2
        assert store.count_notices(channel_id="C2222") == 1
        store.close()


class TestRemindExcludes:
    def test_add_and_list_excludes(self) -> None:
        store = NoticeStore()
        store.add_remind_exclude("U001")
        store.add_remind_exclude("U002")
        excludes = store.list_remind_excludes()
        assert set(excludes) == {"U001", "U002"}
        store.close()

    def test_remove_exclude(self) -> None:
        store = NoticeStore()
        store.add_remind_exclude("U001")
        store.add_remind_exclude("U002")
        store.remove_remind_exclude("U001")
        excludes = store.list_remind_excludes()
        assert excludes == ["U002"]
        store.close()

    def test_add_duplicate_exclude(self) -> None:
        store = NoticeStore()
        store.add_remind_exclude("U001")
        store.add_remind_exclude("U001")
        excludes = store.list_remind_excludes()
        assert excludes == ["U001"]
        store.close()


class TestDashboardNewFormat:
    def test_dashboard_with_response_rates(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice()]
        rates = {notices[0].notice_id: "2/5"}
        modal = build_notice_dashboard_modal(notices, response_rates=rates)
        section = [b for b in modal["blocks"] if b["type"] == "section"][0]
        assert "응답률: 2/5" in section["text"]["text"]

    def test_deleted_notice_author_sees_status_only(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice(message_ts="", author_id="U1234")]
        modal = build_notice_dashboard_modal(notices, viewer_id="U1234")
        section = [b for b in modal["blocks"] if b["type"] == "section"][0]
        assert "삭제됨" in section["text"]["text"]
        actions = [b for b in modal["blocks"] if b["type"] == "actions"][0]
        action_ids = [e["action_id"] for e in actions["elements"]]
        # Deleted: no remind, no edit, no delete — only status
        assert len(action_ids) == 1
        assert any("notice_status_" in a for a in action_ids)

    def test_deleted_notice_non_author_sees_status_only(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice(message_ts="", author_id="U_AUTHOR")]
        modal = build_notice_dashboard_modal(notices, viewer_id="U_OTHER")
        actions = [b for b in modal["blocks"] if b["type"] == "actions"][0]
        action_ids = [e["action_id"] for e in actions["elements"]]
        assert len(action_ids) == 1
        assert any("notice_status_" in a for a in action_ids)


class TestPaginationBlocks:
    def _get_pagination_actions(self, view: dict) -> list:  # type: ignore[type-arg]
        all_actions = [b for b in view["blocks"] if b["type"] == "actions"]
        return [
            b for b in all_actions if any(e.get("action_id", "").startswith("dashboard_page_") for e in b["elements"])
        ]

    def test_first_page_has_next_only(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice()]
        view = build_home_tab_view(notices, total_count=12, offset=0, page_size=5)
        pagination = self._get_pagination_actions(view)
        assert len(pagination) == 1
        btns = pagination[0]["elements"]
        action_ids = [b["action_id"] for b in btns]
        # No "이전" button on first page
        assert not any("이전" in b["text"]["text"] for b in btns)
        # Has info button and "다음" button
        assert "dashboard_page_noop" in action_ids
        assert any("다음" in b["text"]["text"] for b in btns)
        # Info button shows count
        info_btn = [b for b in btns if b["action_id"] == "dashboard_page_noop"][0]
        assert "1-5 / 12건" in info_btn["text"]["text"]

    def test_middle_page_has_both_nav(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice()]
        view = build_home_tab_view(notices, total_count=15, offset=5, page_size=5)
        pagination = self._get_pagination_actions(view)
        assert len(pagination) == 1
        btns = pagination[0]["elements"]
        assert any("이전" in b["text"]["text"] for b in btns)
        assert any("다음" in b["text"]["text"] for b in btns)

    def test_last_page_has_prev_only(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice()]
        view = build_home_tab_view(notices, total_count=12, offset=10, page_size=5)
        pagination = self._get_pagination_actions(view)
        assert len(pagination) == 1
        btns = pagination[0]["elements"]
        assert any("이전" in b["text"]["text"] for b in btns)
        assert not any("다음" in b["text"]["text"] for b in btns)

    def test_no_pagination_when_fits_single_page(self) -> None:
        notices: list[Notice | MeetingNotice] = [_make_notice()]
        view = build_home_tab_view(notices, total_count=3, offset=0, page_size=5)
        pagination = self._get_pagination_actions(view)
        assert len(pagination) == 0


class TestDeleteConfirmModal:
    def test_build_delete_confirm_modal(self) -> None:
        notice = _make_notice()
        modal = build_notice_delete_confirm_modal(notice)
        assert modal["type"] == "modal"
        assert modal["callback_id"] == "notice_delete_confirm"
        assert modal["private_metadata"] == notice.notice_id
        assert "삭제" in modal["submit"]["text"]

    def test_delete_confirm_modal_meeting(self) -> None:
        notice = _make_meeting_notice()
        modal = build_notice_delete_confirm_modal(notice)
        section_text = modal["blocks"][0]["text"]["text"]
        assert "회의" in section_text


class TestRemindExcludeModal:
    def test_build_exclude_modal_empty(self) -> None:
        modal = build_remind_exclude_modal([])
        assert modal["callback_id"] == "remind_exclude_modal"
        element = modal["blocks"][1]["element"]
        assert element["type"] == "multi_users_select"
        assert "initial_users" not in element

    def test_build_exclude_modal_with_users(self) -> None:
        modal = build_remind_exclude_modal(["U001", "U002"])
        element = modal["blocks"][1]["element"]
        assert element["initial_users"] == ["U001", "U002"]


class TestStatusOriginalContent:
    def test_notice_status_shows_content(self) -> None:
        notice = _make_notice(content="공지 본문 내용입니다")
        msg = build_notice_status_message(notice, ["U001", "U002"])
        content_section = msg["blocks"][2]
        assert "공지 본문 내용입니다" in content_section["text"]["text"]

    def test_notice_status_shows_author(self) -> None:
        notice = _make_notice(author_id="U_WRITER")
        msg = build_notice_status_message(notice, ["U001"])
        context_block = msg["blocks"][3]
        assert "<@U_WRITER>" in context_block["elements"][0]["text"]

    def test_meeting_status_shows_details(self) -> None:
        notice = _make_meeting_notice(location="회의실 B", agenda="새 안건 논의")
        msg = build_meeting_status_message(notice, ["U001"])
        fields_section = msg["blocks"][2]
        field_texts = [f["text"] for f in fields_section["fields"]]
        assert any("회의실 B" in t for t in field_texts)
        agenda_section = msg["blocks"][3]
        assert "새 안건 논의" in agenda_section["text"]["text"]


class TestDeleteAction:
    def test_delete_button_non_author(self) -> None:
        store = NoticeStore()
        notice = _make_notice(author_id="U_AUTHOR")
        store.create_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U_OTHER"},
            "channel": {"id": "C1234"},
            "actions": [{"type": "button", "action_id": f"notice_delete_{notice.notice_id}"}],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.chat_postEphemeral") as mock_ephemeral:
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_ephemeral.assert_called_once()
            assert "작성자만" in mock_ephemeral.call_args.kwargs.get("text", "")

    def test_delete_button_author_opens_confirm(self) -> None:
        store = NoticeStore()
        notice = _make_notice(author_id="U_AUTHOR")
        store.create_notice(notice)
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U_AUTHOR"},
            "channel": {"id": "C1234"},
            "actions": [{"type": "button", "action_id": f"notice_delete_{notice.notice_id}"}],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.views_open") as mock_views_open:
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_views_open.assert_called_once()
            view = mock_views_open.call_args.kwargs.get("view", {})
            assert view["callback_id"] == "notice_delete_confirm"

    def test_delete_confirm_deletes_message(self) -> None:
        store = NoticeStore()
        notice = _make_notice(author_id="U_AUTHOR", message_ts="1707350400.000001")
        store.create_notice(notice)
        app = _create_test_app(store)

        view_payload = {
            "type": "view_submission",
            "user": {"id": "U_AUTHOR"},
            "view": {
                "type": "modal",
                "callback_id": "notice_delete_confirm",
                "private_metadata": notice.notice_id,
                "state": {"values": {}},
            },
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with (
            patch("slack_sdk.web.client.WebClient.chat_delete") as mock_delete,
            patch("slack_sdk.web.client.WebClient.chat_postMessage"),
            patch("slack_sdk.web.client.WebClient.views_publish"),
            patch("slack_sdk.web.client.WebClient.conversations_members") as mock_members,
        ):
            mock_members.return_value = {"members": []}
            request = BoltRequest(
                body=json.dumps(view_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_delete.assert_called_once()
            # message_ts should be cleared (soft delete)
            retrieved = store.get_notice(notice.notice_id)
            assert retrieved is not None
            assert retrieved.message_ts == ""


class TestHomeCreateButtons:
    def _dispatch_action(self, app: App, action_id: str) -> None:
        payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "actions": [{"type": "button", "action_id": action_id}],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }
        with patch("slack_sdk.web.client.WebClient.views_open") as mock_open:
            request = BoltRequest(
                body=json.dumps(payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_open.assert_called_once()
            view = mock_open.call_args.kwargs.get("view", {})
            return view  # type: ignore[return-value]

    def test_home_notice_create_opens_modal(self) -> None:
        app = _create_test_app(NoticeStore())
        view = self._dispatch_action(app, "home_notice_create")
        assert view["callback_id"] == "notice_create_modal"  # type: ignore[index]

    def test_home_meeting_notice_create_opens_modal(self) -> None:
        app = _create_test_app(NoticeStore())
        view = self._dispatch_action(app, "home_meeting_notice_create")
        assert view["callback_id"] == "meeting_notice_modal"  # type: ignore[index]


class TestPaginationAction:
    def test_dashboard_page_action(self) -> None:
        store = NoticeStore()
        for i in range(7):
            store.create_notice(_make_notice(f"notice_{i:03d}_aaaa", created_at=1707350400.0 + i))
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "actions": [{"type": "button", "action_id": "dashboard_page_5"}],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with (
            patch("slack_sdk.web.client.WebClient.conversations_members") as mock_members,
            patch("slack_sdk.web.client.WebClient.views_publish") as mock_publish,
        ):
            mock_members.return_value = {"members": []}
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_publish.assert_called_once()
            view = mock_publish.call_args.kwargs.get("view", {})
            assert view["type"] == "home"


class TestExcludeManageAction:
    def test_exclude_manage_opens_modal(self) -> None:
        store = NoticeStore()
        store.add_remind_exclude("U001")
        app = _create_test_app(store)

        action_payload = {
            "type": "block_actions",
            "user": {"id": "U999"},
            "actions": [{"type": "button", "action_id": "remind_exclude_manage"}],
            "trigger_id": "T123",
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.views_open") as mock_views_open:
            request = BoltRequest(
                body=json.dumps(action_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            mock_views_open.assert_called_once()
            view = mock_views_open.call_args.kwargs.get("view", {})
            assert view["callback_id"] == "remind_exclude_modal"

    def test_exclude_submission_updates_store(self) -> None:
        store = NoticeStore()
        store.add_remind_exclude("U_OLD")
        app = _create_test_app(store)

        view_payload = {
            "type": "view_submission",
            "user": {"id": "U999"},
            "view": {
                "type": "modal",
                "callback_id": "remind_exclude_modal",
                "private_metadata": "",
                "state": {
                    "values": {
                        "exclude_block": {
                            "remind_exclude_users": {
                                "selected_users": ["U_NEW1", "U_NEW2"],
                            }
                        }
                    }
                },
            },
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with (
            patch("slack_sdk.web.client.WebClient.chat_postMessage"),
            patch("slack_sdk.web.client.WebClient.views_publish"),
            patch("slack_sdk.web.client.WebClient.conversations_members") as mock_members,
        ):
            mock_members.return_value = {"members": []}
            request = BoltRequest(
                body=json.dumps(view_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            excludes = set(store.list_remind_excludes())
            assert excludes == {"U_NEW1", "U_NEW2"}
            assert "U_OLD" not in excludes

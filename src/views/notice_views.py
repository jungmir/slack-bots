from __future__ import annotations

import datetime
from typing import Any

from src.store.models import AttendanceStatus, MeetingNotice, Notice, NoticeType


_KST = datetime.timezone(datetime.timedelta(hours=9))


def _format_ts(ts: float, fmt: str = "%Y-%m-%d %H:%M") -> str:
    return datetime.datetime.fromtimestamp(ts, tz=_KST).strftime(fmt)


def build_notice_create_modal(channel_id: str = "") -> dict[str, Any]:
    channel_element: dict[str, Any] = {
        "type": "channels_select",
        "action_id": "channel_input",
        "placeholder": {"type": "plain_text", "text": "채널 선택"},
    }
    if channel_id:
        channel_element["initial_channel"] = channel_id
    return {
        "type": "modal",
        "callback_id": "notice_create_modal",
        "title": {"type": "plain_text", "text": "공지 작성"},
        "submit": {"type": "plain_text", "text": "등록"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "title_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "title_input",
                    "placeholder": {"type": "plain_text", "text": "공지 제목을 입력하세요"},
                },
                "label": {"type": "plain_text", "text": "제목"},
            },
            {
                "type": "input",
                "block_id": "content_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "content_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "공지 내용을 입력하세요"},
                },
                "label": {"type": "plain_text", "text": "내용"},
            },
            {
                "type": "input",
                "block_id": "channel_block",
                "element": channel_element,
                "label": {"type": "plain_text", "text": "대상 채널"},
            },
        ],
    }


def build_meeting_notice_modal(channel_id: str = "") -> dict[str, Any]:
    channel_element: dict[str, Any] = {
        "type": "channels_select",
        "action_id": "channel_input",
        "placeholder": {"type": "plain_text", "text": "채널 선택"},
    }
    if channel_id:
        channel_element["initial_channel"] = channel_id
    return {
        "type": "modal",
        "callback_id": "meeting_notice_modal",
        "title": {"type": "plain_text", "text": "회의 공지 작성"},
        "submit": {"type": "plain_text", "text": "등록"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "title_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "title_input",
                    "placeholder": {"type": "plain_text", "text": "회의 제목을 입력하세요"},
                },
                "label": {"type": "plain_text", "text": "제목"},
            },
            {
                "type": "input",
                "block_id": "datetime_block",
                "element": {
                    "type": "datetimepicker",
                    "action_id": "datetime_input",
                },
                "label": {"type": "plain_text", "text": "일시"},
            },
            {
                "type": "input",
                "block_id": "location_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "location_input",
                    "placeholder": {"type": "plain_text", "text": "장소를 입력하세요"},
                },
                "label": {"type": "plain_text", "text": "장소"},
            },
            {
                "type": "input",
                "block_id": "agenda_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "agenda_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "안건을 입력하세요"},
                },
                "label": {"type": "plain_text", "text": "안건"},
            },
            {
                "type": "input",
                "block_id": "channel_block",
                "element": channel_element,
                "label": {"type": "plain_text", "text": "대상 채널"},
            },
        ],
    }


def build_notice_message(notice: Notice) -> dict[str, Any]:
    return {
        "text": f"[공지] {notice.title}",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"[공지] {notice.title}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": notice.content},
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"작성자: <@{notice.author_id}> | {_format_ts(notice.created_at)}",
                    }
                ],
            },
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "확인"},
                        "action_id": f"notice_confirm_{notice.notice_id}",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "현황 보기"},
                        "action_id": f"notice_status_{notice.notice_id}",
                    },
                ],
            },
        ],
    }


def build_meeting_notice_message(notice: MeetingNotice) -> dict[str, Any]:
    dt_display = notice.meeting_datetime
    if notice.meeting_datetime.isdigit():
        dt_display = _format_ts(float(notice.meeting_datetime))

    return {
        "text": f"[회의 공지] {notice.title}",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"[회의 공지] {notice.title}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*일시:*\n{dt_display}"},
                    {"type": "mrkdwn", "text": f"*장소:*\n{notice.location}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*안건:*\n{notice.agenda}"},
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"작성자: <@{notice.author_id}> | {_format_ts(notice.created_at)}",
                    }
                ],
            },
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "온라인 참석"},
                        "action_id": f"meeting_attend_online_{notice.notice_id}",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "오프라인 참석"},
                        "action_id": f"meeting_attend_offline_{notice.notice_id}",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "불참"},
                        "action_id": f"meeting_attend_absent_{notice.notice_id}",
                        "style": "danger",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "현황 보기"},
                        "action_id": f"notice_status_{notice.notice_id}",
                    },
                ],
            },
        ],
    }


def build_notice_list_message(notices: list[Notice | MeetingNotice]) -> dict[str, Any]:
    if not notices:
        return {"text": "등록된 공지가 없습니다.", "blocks": []}

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "공지 목록"},
        }
    ]

    for notice in notices:
        type_label = "회의" if notice.notice_type == NoticeType.MEETING else "일반"
        dt_str = _format_ts(notice.created_at, "%Y-%m-%d")
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*[{type_label}] {notice.title}*\n`{notice.notice_id}` | {dt_str} | <@{notice.author_id}>",
                },
            }
        )

    return {"text": "공지 목록", "blocks": blocks}


def build_notice_status_message(notice: Notice, members: list[str]) -> dict[str, Any]:
    read_users = notice.read_by
    unread_users = [m for m in members if m not in read_users]

    read_text = ", ".join(f"<@{u}>" for u in read_users) if read_users else "없음"
    unread_text = ", ".join(f"<@{u}>" for u in unread_users) if unread_users else "없음"

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"읽음 현황: {notice.title}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": notice.content},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"작성자: <@{notice.author_id}> | {_format_ts(notice.created_at)}",
                }
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (f"*확인 ({len(read_users)}명):* {read_text}\n*미확인 ({len(unread_users)}명):* {unread_text}"),
            },
        },
    ]

    return {"text": f"공지 읽음 현황: {notice.title}", "blocks": blocks}


def build_notice_dashboard_modal(
    notices: list[Notice | MeetingNotice],
    *,
    response_rates: dict[str, str] | None = None,
    viewer_id: str = "",
) -> dict[str, Any]:
    return {
        "type": "modal",
        "callback_id": "notice_dashboard_modal",
        "title": {"type": "plain_text", "text": "공지 대시보드"},
        "close": {"type": "plain_text", "text": "닫기"},
        "blocks": _build_dashboard_blocks(
            notices,
            response_rates=response_rates,
            viewer_id=viewer_id,
        ),
    }


def build_meeting_status_message(notice: MeetingNotice, members: list[str]) -> dict[str, Any]:
    dt_display = notice.meeting_datetime
    if notice.meeting_datetime.isdigit():
        dt_display = _format_ts(float(notice.meeting_datetime))

    online = [u for u, s in notice.attendance.items() if s == AttendanceStatus.ONLINE]
    offline = [u for u, s in notice.attendance.items() if s == AttendanceStatus.OFFLINE]
    absent = [u for u, s in notice.attendance.items() if s == AttendanceStatus.ABSENT]
    no_response = [m for m in members if m not in notice.attendance]

    def _user_list(users: list[str]) -> str:
        return ", ".join(f"<@{u}>" for u in users) if users else "없음"

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"참석 현황: {notice.title}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*일시:*\n{dt_display}"},
                {"type": "mrkdwn", "text": f"*장소:*\n{notice.location}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*안건:*\n{notice.agenda}"},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"작성자: <@{notice.author_id}> | {_format_ts(notice.created_at)}",
                }
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*온라인 ({len(online)}명):* {_user_list(online)}\n"
                    f"*오프라인 ({len(offline)}명):* {_user_list(offline)}\n"
                    f"*불참 ({len(absent)}명):* {_user_list(absent)}\n"
                    f"*미응답 ({len(no_response)}명):* {_user_list(no_response)}"
                ),
            },
        },
    ]

    return {"text": f"회의 참석 현황: {notice.title}", "blocks": blocks}


def build_notice_status_modal(notice: Notice, members: list[str]) -> dict[str, Any]:
    msg = build_notice_status_message(notice, members)
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "읽음 현황"},
        "close": {"type": "plain_text", "text": "닫기"},
        "blocks": msg["blocks"],
    }


def build_meeting_status_modal(notice: MeetingNotice, members: list[str]) -> dict[str, Any]:
    msg = build_meeting_status_message(notice, members)
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "참석 현황"},
        "close": {"type": "plain_text", "text": "닫기"},
        "blocks": msg["blocks"],
    }


def build_notice_edit_modal(notice: Notice) -> dict[str, Any]:
    return {
        "type": "modal",
        "callback_id": "notice_edit_modal",
        "private_metadata": notice.notice_id,
        "title": {"type": "plain_text", "text": "공지 수정"},
        "submit": {"type": "plain_text", "text": "저장"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "title_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "title_input",
                    "initial_value": notice.title,
                },
                "label": {"type": "plain_text", "text": "제목"},
            },
            {
                "type": "input",
                "block_id": "content_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "content_input",
                    "multiline": True,
                    "initial_value": notice.content,
                },
                "label": {"type": "plain_text", "text": "내용"},
            },
        ],
    }


def build_meeting_notice_edit_modal(notice: MeetingNotice) -> dict[str, Any]:
    return {
        "type": "modal",
        "callback_id": "meeting_notice_edit_modal",
        "private_metadata": notice.notice_id,
        "title": {"type": "plain_text", "text": "회의 공지 수정"},
        "submit": {"type": "plain_text", "text": "저장"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "title_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "title_input",
                    "initial_value": notice.title,
                },
                "label": {"type": "plain_text", "text": "제목"},
            },
            {
                "type": "input",
                "block_id": "datetime_block",
                "element": {
                    "type": "datetimepicker",
                    "action_id": "datetime_input",
                    **(
                        {"initial_date_time": int(notice.meeting_datetime)} if notice.meeting_datetime.isdigit() else {}
                    ),
                },
                "label": {"type": "plain_text", "text": "일시"},
            },
            {
                "type": "input",
                "block_id": "location_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "location_input",
                    "initial_value": notice.location,
                },
                "label": {"type": "plain_text", "text": "장소"},
            },
            {
                "type": "input",
                "block_id": "agenda_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "agenda_input",
                    "multiline": True,
                    "initial_value": notice.agenda,
                },
                "label": {"type": "plain_text", "text": "안건"},
            },
        ],
    }


def _build_dashboard_blocks(
    notices: list[Notice | MeetingNotice],
    *,
    response_rates: dict[str, str] | None = None,
    total_count: int = 0,
    offset: int = 0,
    page_size: int = 5,
    include_pagination: bool = False,
    viewer_id: str = "",
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    if not notices:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "등록된 공지가 없습니다."},
            }
        )
    else:
        for notice in notices:
            type_label = "회의" if notice.notice_type == NoticeType.MEETING else "일반"
            dt_str = _format_ts(notice.created_at, "%Y-%m-%d")
            is_deleted = not notice.message_ts
            is_author = viewer_id == notice.author_id

            title_text = f"*[{type_label}] {notice.title}* ({dt_str})"
            if is_deleted:
                title_text += "  :no_entry_sign: _삭제됨_"

            rate = (response_rates or {}).get(notice.notice_id, "-")
            meta_text = f"작성자: <@{notice.author_id}> | 응답률: {rate} | ID: `{notice.notice_id}`"

            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"{title_text}\n{meta_text}"},
                }
            )

            buttons: list[dict[str, Any]] = [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "현황 보기"},
                    "action_id": f"notice_status_{notice.notice_id}",
                },
            ]
            if is_author and not is_deleted:
                buttons.append(
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "리마인드"},
                        "action_id": f"notice_remind_{notice.notice_id}",
                    }
                )
                buttons.append(
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "수정"},
                        "action_id": f"notice_edit_{notice.notice_id}",
                    }
                )
                buttons.append(
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "삭제"},
                        "action_id": f"notice_delete_{notice.notice_id}",
                        "style": "danger",
                    }
                )

            blocks.append({"type": "actions", "elements": buttons})
            blocks.append({"type": "divider"})

    if include_pagination and total_count > page_size:
        current_page = offset // page_size
        total_pages = (total_count + page_size - 1) // page_size
        start = offset + 1
        end = min(offset + page_size, total_count)

        nav_buttons: list[dict[str, Any]] = []
        if current_page > 0:
            nav_buttons.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "◀ 이전"},
                    "action_id": f"dashboard_page_{(current_page - 1) * page_size}",
                }
            )
        nav_buttons.append(
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": f"{start}-{end} / {total_count}건",
                },
                "action_id": "dashboard_page_noop",
            }
        )
        if current_page < total_pages - 1:
            nav_buttons.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "다음 ▶"},
                    "action_id": f"dashboard_page_{(current_page + 1) * page_size}",
                }
            )
        blocks.append({"type": "actions", "elements": nav_buttons})

    return blocks


def build_home_tab_view(
    notices: list[Notice | MeetingNotice],
    *,
    response_rates: dict[str, str] | None = None,
    total_count: int = 0,
    offset: int = 0,
    page_size: int = 5,
    viewer_id: str = "",
) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "공지 대시보드"},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "공지 작성"},
                    "action_id": "home_notice_create",
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "회의 공지 작성"},
                    "action_id": "home_meeting_notice_create",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "리마인드 예외 목록 관리"},
                    "action_id": "remind_exclude_manage",
                },
            ],
        },
        {"type": "divider"},
    ]
    blocks.extend(
        _build_dashboard_blocks(
            notices,
            response_rates=response_rates,
            total_count=total_count,
            offset=offset,
            page_size=page_size,
            include_pagination=True,
            viewer_id=viewer_id,
        )
    )
    return {
        "type": "home",
        "blocks": blocks,
    }


def build_notice_delete_confirm_modal(notice: Notice | MeetingNotice) -> dict[str, Any]:
    type_label = "회의" if notice.notice_type == NoticeType.MEETING else "일반"
    return {
        "type": "modal",
        "callback_id": "notice_delete_confirm",
        "private_metadata": notice.notice_id,
        "title": {"type": "plain_text", "text": "공지 삭제 확인"},
        "submit": {"type": "plain_text", "text": "삭제"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"다음 공지의 채널 메시지를 삭제합니다.\n\n"
                        f"*[{type_label}] {notice.title}*\n"
                        f"ID: `{notice.notice_id}`"
                    ),
                },
            }
        ],
    }


def build_remind_exclude_modal(excludes: list[str]) -> dict[str, Any]:
    element: dict[str, Any] = {
        "type": "multi_users_select",
        "action_id": "remind_exclude_users",
        "placeholder": {"type": "plain_text", "text": "사용자 선택"},
    }
    if excludes:
        element["initial_users"] = excludes

    return {
        "type": "modal",
        "callback_id": "remind_exclude_modal",
        "title": {"type": "plain_text", "text": "리마인드 예외 관리"},
        "submit": {"type": "plain_text", "text": "저장"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "리마인드에서 제외할 사용자를 선택하세요.\n"
                        "선택된 사용자는 모든 공지의 리마인드 대상에서 제외됩니다."
                    ),
                },
            },
            {
                "type": "input",
                "block_id": "exclude_block",
                "optional": True,
                "element": element,
                "label": {"type": "plain_text", "text": "예외 사용자"},
            },
        ],
    }

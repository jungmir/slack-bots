from __future__ import annotations

from typing import Any

from src.clients.dooray_client import DoorayMember, DoorayTag, DoorayTask


def build_dooray_usage_modal() -> dict[str, Any]:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "두레이 사용법"},
        "close": {"type": "plain_text", "text": "닫기"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*`/dooray` 사용법:*\n\n"
                        "• `/dooray me` — 나에게 할당된 업무 목록\n"
                        "• `/dooray create` — 업무 생성 (모달)\n"
                        "• `/dooray setup` — Slack↔Dooray 사용자 연결\n"
                        "• `/dooray setup search <이름>` — Dooray 멤버 검색"
                    ),
                },
            }
        ],
    }


def build_dooray_task_list_modal(tasks: list[DoorayTask]) -> dict[str, Any]:
    if not tasks:
        blocks: list[dict[str, Any]] = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "할당된 진행중 업무가 없습니다."},
            }
        ]
    else:
        blocks = []
        for task in tasks:
            status = task.workflow_name or task.workflow_class
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{task.subject}*\nID: `{task.id}` | 상태: {status}",
                    },
                }
            )
            blocks.append({"type": "divider"})

    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "내 업무 목록"},
        "close": {"type": "plain_text", "text": "닫기"},
        "blocks": blocks,
    }


def build_dooray_create_task_modal(
    tags: list[DoorayTag] | None = None,
) -> dict[str, Any]:
    tag_options = [
        {
            "text": {"type": "plain_text", "text": t.name or t.id},
            "value": t.id,
        }
        for t in (tags or [])
        if t.id
    ]
    if tag_options:
        tag_element: dict[str, Any] = {
            "type": "multi_static_select",
            "action_id": "tag_input",
            "placeholder": {"type": "plain_text", "text": "태그를 선택하세요"},
            "options": tag_options,
        }
    else:
        tag_element = {
            "type": "plain_text_input",
            "action_id": "tag_input",
            "placeholder": {"type": "plain_text", "text": "태그 ID (쉼표로 구분)"},
        }

    blocks: list[dict[str, Any]] = [
        {
            "type": "input",
            "block_id": "subject_block",
            "element": {
                "type": "plain_text_input",
                "action_id": "subject_input",
                "placeholder": {"type": "plain_text", "text": "업무 제목을 입력하세요"},
            },
            "label": {"type": "plain_text", "text": "제목"},
        },
        {
            "type": "input",
            "block_id": "body_block",
            "optional": True,
            "element": {
                "type": "plain_text_input",
                "action_id": "body_input",
                "multiline": True,
                "placeholder": {"type": "plain_text", "text": "업무 내용을 입력하세요"},
            },
            "label": {"type": "plain_text", "text": "내용"},
        },
        {
            "type": "input",
            "block_id": "tag_block",
            "optional": True,
            "element": tag_element,
            "label": {"type": "plain_text", "text": "태그"},
        },
        {
            "type": "input",
            "block_id": "due_date_block",
            "optional": True,
            "element": {
                "type": "datepicker",
                "action_id": "due_date_input",
                "placeholder": {"type": "plain_text", "text": "만기일 선택"},
            },
            "label": {"type": "plain_text", "text": "만기일"},
        },
    ]

    return {
        "type": "modal",
        "callback_id": "dooray_create_task_modal",
        "title": {"type": "plain_text", "text": "두레이 업무 생성"},
        "submit": {"type": "plain_text", "text": "생성"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": blocks,
    }


def build_dooray_result_modal(title: str, message: str) -> dict[str, Any]:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": title},
        "close": {"type": "plain_text", "text": "닫기"},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
            }
        ],
    }


def build_dooray_setup_modal() -> dict[str, Any]:
    return {
        "type": "modal",
        "callback_id": "dooray_setup_modal",
        "title": {"type": "plain_text", "text": "Dooray 계정 연결"},
        "submit": {"type": "plain_text", "text": "검색"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Dooray 계정을 연결하려면 이름을 검색하세요.",
                },
            },
            {
                "type": "input",
                "block_id": "search_name_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "search_name_input",
                    "placeholder": {"type": "plain_text", "text": "이름을 입력하세요"},
                },
                "label": {"type": "plain_text", "text": "이름 검색"},
            },
        ],
    }


def build_dooray_setup_select_modal(members: list[DoorayMember]) -> dict[str, Any]:
    if not members:
        return {
            "type": "modal",
            "title": {"type": "plain_text", "text": "검색 결과"},
            "close": {"type": "plain_text", "text": "닫기"},
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "검색 결과가 없습니다."},
                }
            ],
        }

    options = [
        {
            "text": {"type": "plain_text", "text": f"{m.name} ({m.email})"},
            "value": m.id,
        }
        for m in members
    ]

    return {
        "type": "modal",
        "callback_id": "dooray_setup_select_modal",
        "title": {"type": "plain_text", "text": "멤버 선택"},
        "submit": {"type": "plain_text", "text": "연결"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "member_select_block",
                "element": {
                    "type": "static_select",
                    "action_id": "member_select_input",
                    "placeholder": {"type": "plain_text", "text": "멤버를 선택하세요"},
                    "options": options,
                },
                "label": {"type": "plain_text", "text": "Dooray 멤버"},
            }
        ],
    }


def build_dooray_member_search_modal(members: list[DoorayMember]) -> dict[str, Any]:
    if not members:
        blocks: list[dict[str, Any]] = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "검색 결과가 없습니다."},
            }
        ]
    else:
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Dooray 멤버 검색 결과"},
            }
        ]
        for m in members:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{m.name}*\nID: `{m.id}` | {m.email}",
                    },
                }
            )

    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "멤버 검색"},
        "close": {"type": "plain_text", "text": "닫기"},
        "blocks": blocks,
    }


def build_dooray_error_modal(message: str) -> dict[str, Any]:
    return build_dooray_result_modal("오류", f"오류가 발생했습니다:\n{message}")


def build_dooray_not_linked_modal() -> dict[str, Any]:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "계정 미연결"},
        "close": {"type": "plain_text", "text": "닫기"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ("Dooray 계정이 연결되지 않았습니다.\n\n`/dooray setup`으로 계정을 연결해주세요."),
                },
            }
        ],
    }

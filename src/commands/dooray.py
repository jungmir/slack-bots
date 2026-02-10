from __future__ import annotations

import logging

from slack_bolt import App
from slack_bolt.context.ack import Ack
from slack_sdk.web import WebClient

from src.clients.dooray_client import DoorayClient
from src.services.dooray_service import DoorayService, DoorayServiceError, UserNotLinkedError
from src.store.dooray_store import DoorayStore
from src.views.dooray_views import (
    build_dooray_create_task_modal,
    build_dooray_error_modal,
    build_dooray_member_search_modal,
    build_dooray_not_linked_modal,
    build_dooray_result_modal,
    build_dooray_setup_modal,
    build_dooray_setup_select_modal,
    build_dooray_task_list_modal,
    build_dooray_usage_modal,
)

logger = logging.getLogger(__name__)


def _parse_csv_input(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def register_dooray_commands(
    app: App,
    dooray_client: DoorayClient,
    dooray_store: DoorayStore,
    default_project_id: str,
) -> None:
    service = DoorayService(
        dooray_client=dooray_client,
        store=dooray_store,
        default_project_id=default_project_id,
    )

    @app.command("/dooray")
    def handle_dooray_command(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        text = str(body.get("text", "")).strip()
        trigger_id = str(body.get("trigger_id", ""))
        user_id = str(body.get("user_id", ""))
        parts = text.split(maxsplit=1)
        subcommand = parts[0] if parts else ""

        if subcommand == "me":
            try:
                tasks = service.get_my_tasks(user_id)
            except UserNotLinkedError:
                client.views_open(trigger_id=trigger_id, view=build_dooray_not_linked_modal())
                return
            except DoorayServiceError as e:
                client.views_open(trigger_id=trigger_id, view=build_dooray_error_modal(str(e)))
                return
            client.views_open(trigger_id=trigger_id, view=build_dooray_task_list_modal(tasks))

        elif subcommand == "create":
            try:
                tags = service.list_project_tags()
            except Exception:
                tags = None
            try:
                project_name = service.get_project_name()
            except Exception:
                project_name = ""
            current_member_id = dooray_store.get_dooray_member_id(user_id) or ""
            modal = build_dooray_create_task_modal(
                default_project_id,
                tags=tags,
                project_name=project_name,
                current_user_member_id=current_member_id,
            )
            client.views_open(trigger_id=trigger_id, view=modal)

        elif subcommand == "done":
            task_id = parts[1].strip() if len(parts) > 1 else ""
            if not task_id:
                client.views_open(
                    trigger_id=trigger_id,
                    view=build_dooray_result_modal("사용법", "사용법: `/dooray done <업무ID>`"),
                )
                return
            try:
                service.complete_task(task_id)
            except DoorayServiceError as e:
                client.views_open(trigger_id=trigger_id, view=build_dooray_error_modal(str(e)))
                return
            client.views_open(
                trigger_id=trigger_id,
                view=build_dooray_result_modal("완료", f"업무가 완료 처리되었습니다.\nID: `{task_id}`"),
            )

        elif subcommand == "comment":
            rest = parts[1].strip() if len(parts) > 1 else ""
            comment_parts = rest.split(maxsplit=1)
            task_id = comment_parts[0] if comment_parts else ""
            content = comment_parts[1] if len(comment_parts) > 1 else ""
            if not task_id or not content:
                client.views_open(
                    trigger_id=trigger_id,
                    view=build_dooray_result_modal("사용법", "사용법: `/dooray comment <업무ID> <내용>`"),
                )
                return
            try:
                service.add_comment(task_id, content)
            except DoorayServiceError as e:
                client.views_open(trigger_id=trigger_id, view=build_dooray_error_modal(str(e)))
                return
            client.views_open(
                trigger_id=trigger_id,
                view=build_dooray_result_modal("완료", f"업무에 코멘트가 추가되었습니다.\nID: `{task_id}`"),
            )

        elif subcommand == "setup":
            rest = parts[1].strip() if len(parts) > 1 else ""
            setup_parts = rest.split(maxsplit=1)
            setup_sub = setup_parts[0] if setup_parts else ""

            if setup_sub == "search":
                search_name = setup_parts[1].strip() if len(setup_parts) > 1 else ""
                if not search_name:
                    client.views_open(
                        trigger_id=trigger_id,
                        view=build_dooray_result_modal("사용법", "사용법: `/dooray setup search <이름>`"),
                    )
                    return
                try:
                    members = service.search_members(search_name)
                except DoorayServiceError as e:
                    client.views_open(trigger_id=trigger_id, view=build_dooray_error_modal(str(e)))
                    return
                client.views_open(trigger_id=trigger_id, view=build_dooray_member_search_modal(members))
            elif setup_sub:
                service.setup_user(user_id, setup_sub)
                client.views_open(
                    trigger_id=trigger_id,
                    view=build_dooray_result_modal("연결 완료", f"Dooray 멤버 ID가 등록되었습니다: `{setup_sub}`"),
                )
            else:
                client.views_open(trigger_id=trigger_id, view=build_dooray_setup_modal())

        else:
            client.views_open(trigger_id=trigger_id, view=build_dooray_usage_modal())

    @app.view("dooray_create_task_modal")
    def handle_dooray_create_task_submission(
        ack: Ack,
        body: dict[str, object],
        view: dict[str, object],
    ) -> None:
        state: dict[str, object] = view.get("state", {})  # type: ignore[assignment]
        values: dict[str, dict[str, dict[str, object]]] = state.get("values", {})  # type: ignore[assignment]
        subject = str(values["subject_block"]["subject_input"].get("value", ""))
        body_text = str(values["body_block"]["body_input"].get("value", "") or "")

        assignee_data = values["assignee_block"]["assignee_input"]
        assignee_selected: list[dict[str, object]] | None = assignee_data.get("selected_options")  # type: ignore[assignment]
        to_member_ids: list[str] | None
        if assignee_selected:
            to_member_ids = [str(opt.get("value", "")) for opt in assignee_selected]
        else:
            assignee_raw = str(assignee_data.get("value", "") or "")
            to_member_ids = _parse_csv_input(assignee_raw) if assignee_raw else None

        tag_data = values["tag_block"]["tag_input"]
        tag_selected: list[dict[str, object]] | None = tag_data.get("selected_options")  # type: ignore[assignment]
        tag_ids: list[str] | None
        if tag_selected:
            tag_ids = [str(opt.get("value", "")) for opt in tag_selected]
        else:
            tag_raw = str(tag_data.get("value", "") or "")
            tag_ids = _parse_csv_input(tag_raw) if tag_raw else None

        due_date = str(values["due_date_block"]["due_date_input"].get("selected_date", "") or "")

        project_id = ""
        if "project_block" in values:
            project_id = str(values["project_block"]["project_input"].get("value", "") or "")

        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")

        try:
            task = service.create_task(
                subject=subject,
                body=body_text,
                project_id=project_id,
                slack_user_id=user_id,
                to_member_ids=to_member_ids,
                tag_ids=tag_ids,
                due_date=due_date,
            )
        except DoorayServiceError as e:
            ack(
                response_action="update",
                view=build_dooray_error_modal(f"업무 생성 실패: {e}"),
            )
            return

        ack(
            response_action="update",
            view=build_dooray_result_modal(
                "업무 생성 완료",
                f"업무가 생성되었습니다.\n\n*{task.subject}*\nID: `{task.id}`",
            ),
        )

    @app.view("dooray_setup_modal")
    def handle_dooray_setup_search(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
        view: dict[str, object],
    ) -> None:
        state: dict[str, object] = view.get("state", {})  # type: ignore[assignment]
        values: dict[str, dict[str, dict[str, object]]] = state.get("values", {})  # type: ignore[assignment]
        search_name = str(values["search_name_block"]["search_name_input"].get("value", ""))

        try:
            members = service.search_members(search_name)
        except DoorayServiceError as e:
            ack()
            user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
            user_id = user.get("id", "")
            client.chat_postMessage(channel=user_id, text=f"멤버 검색 실패: {e}")
            return

        modal = build_dooray_setup_select_modal(members)
        ack(response_action="update", view=modal)

    @app.view("dooray_setup_select_modal")
    def handle_dooray_setup_select(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
        view: dict[str, object],
    ) -> None:
        ack()
        state: dict[str, object] = view.get("state", {})  # type: ignore[assignment]
        values: dict[str, dict[str, dict[str, object]]] = state.get("values", {})  # type: ignore[assignment]
        selected: dict[str, object] = values["member_select_block"]["member_select_input"].get(  # type: ignore[assignment]
            "selected_option", {}
        )
        member_id = str(selected.get("value", "")) if isinstance(selected, dict) else ""

        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")

        if member_id:
            service.setup_user(user_id, member_id)
            client.chat_postMessage(
                channel=user_id,
                text=f"Dooray 계정이 연결되었습니다. (멤버 ID: `{member_id}`)",
            )

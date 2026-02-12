from __future__ import annotations

from slack_bolt import App
from slack_bolt.context.ack import Ack
from slack_sdk.web import WebClient

from src.clients.dooray_client import DoorayClient
from src.services.dooray_service import DoorayService, DoorayServiceError, UserNotLinkedError
from src.store.dooray_store import DoorayStore
from src.views.dooray_views import (
    build_dooray_create_task_modal,
    build_dooray_error_modal,
    build_dooray_not_linked_modal,
    build_dooray_result_modal,
    build_dooray_setup_modal,
    build_dooray_setup_select_modal,
    build_dooray_task_list_modal,
)


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

    @app.command("/내업무")
    def handle_my_tasks_command(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        trigger_id = str(body.get("trigger_id", ""))
        user_id = str(body.get("user_id", ""))
        try:
            tasks = service.get_my_tasks(user_id)
        except UserNotLinkedError:
            client.views_open(trigger_id=trigger_id, view=build_dooray_not_linked_modal())
            return
        except DoorayServiceError as e:
            client.views_open(trigger_id=trigger_id, view=build_dooray_error_modal(str(e)))
            return
        client.views_open(trigger_id=trigger_id, view=build_dooray_task_list_modal(tasks))

    @app.command("/새업무")
    def handle_create_task_command(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        trigger_id = str(body.get("trigger_id", ""))
        try:
            tags = service.list_project_tags()
        except Exception:
            tags = None
        modal = build_dooray_create_task_modal(tags=tags)
        client.views_open(trigger_id=trigger_id, view=modal)

    @app.command("/두레이연동")
    def handle_dooray_setup_command(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        trigger_id = str(body.get("trigger_id", ""))
        client.views_open(trigger_id=trigger_id, view=build_dooray_setup_modal())

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

        tag_data = values["tag_block"]["tag_input"]
        tag_selected: list[dict[str, object]] | None = tag_data.get("selected_options")  # type: ignore[assignment]
        tag_ids: list[str] | None
        if tag_selected:
            tag_ids = [str(opt.get("value", "")) for opt in tag_selected]
        else:
            tag_raw = str(tag_data.get("value", "") or "")
            tag_ids = _parse_csv_input(tag_raw) if tag_raw else None

        due_date = str(values["due_date_block"]["due_date_input"].get("selected_date", "") or "")

        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")

        try:
            task = service.create_task(
                subject=subject,
                body=body_text,
                slack_user_id=user_id,
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

from __future__ import annotations

import logging
import re

from slack_bolt import App
from slack_bolt.context.ack import Ack
from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient

from src.services.notice_service import NoticeService
from src.store.notice_store import NoticeStore
from src.views.notice_views import (
    build_home_tab_view,
    build_meeting_notice_modal,
    build_notice_create_modal,
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 3


def _publish_home_tab(
    client: WebClient, user_id: str, store: NoticeStore, offset: int = 0,
) -> None:
    try:
        notices = store.list_notices(limit=PAGE_SIZE, offset=offset)
        total_count = store.count_notices()

        service = NoticeService(store, client)
        rates = service.compute_response_rates(notices)

        view = build_home_tab_view(
            notices,
            response_rates=rates,
            total_count=total_count,
            offset=offset,
            page_size=PAGE_SIZE,
            viewer_id=user_id,
        )
        logger.info("Publishing Home Tab for user %s (offset=%d, total=%d)", user_id, offset, total_count)
        client.views_publish(user_id=user_id, view=view)
    except SlackApiError:
        logger.exception("Failed to publish Home Tab for user %s", user_id)


def register_home_events(app: App, store: NoticeStore) -> None:
    @app.event("app_home_opened")
    def handle_app_home_opened(
        event: dict[str, object],
        client: WebClient,
    ) -> None:
        if event.get("tab") != "home":
            return

        user_id = str(event.get("user", ""))
        if not user_id:
            logger.warning("app_home_opened event received with empty user_id")
            return

        _publish_home_tab(client, user_id, store)

    @app.action(re.compile(r"^dashboard_page_(\d+)$"))
    def handle_dashboard_page(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        actions: list[dict[str, str]] = body.get("actions", [])  # type: ignore[assignment]
        action_id = actions[0].get("action_id", "") if actions else ""
        match = re.match(r"^dashboard_page_(\d+)$", action_id)
        if not match:
            return

        offset = int(match.group(1))
        user: dict[str, str] = body.get("user", {})  # type: ignore[assignment]
        user_id = user.get("id", "")

        _publish_home_tab(client, user_id, store, offset)

    @app.action("dashboard_page_noop")
    def handle_dashboard_page_noop(ack: Ack) -> None:
        ack()

    @app.action("home_notice_create")
    def handle_home_notice_create(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        trigger_id = str(body.get("trigger_id", ""))
        client.views_open(trigger_id=trigger_id, view=build_notice_create_modal())

    @app.action("home_meeting_notice_create")
    def handle_home_meeting_notice_create(
        ack: Ack,
        body: dict[str, object],
        client: WebClient,
    ) -> None:
        ack()
        trigger_id = str(body.get("trigger_id", ""))
        client.views_open(trigger_id=trigger_id, view=build_meeting_notice_modal())

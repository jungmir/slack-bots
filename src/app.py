from __future__ import annotations

import logging
from pathlib import Path

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.context.ack import Ack
from slack_bolt.context.say import Say

from src.commands.notice import register_notice_commands
from src.config import Settings
from src.events.home import register_home_events
from src.store.notice_store import NoticeStore

DEFAULT_DB_DIR = Path("data")
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "notices.db"


def create_app(
    settings: Settings,
    *,
    request_verification_enabled: bool = True,
    notice_store: NoticeStore | None = None,
) -> App:
    logging.basicConfig(level=settings.log_level)

    app = App(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
        request_verification_enabled=request_verification_enabled,
    )

    @app.command("/ping")
    def handle_ping(ack: Ack) -> None:
        ack(text="pong :table_tennis_paddle_and_ball:")

    @app.event("app_mention")
    def handle_app_mention(event: dict[str, object], say: Say) -> None:
        user = event.get("user", "")
        say(text=f"<@{user}> 안녕하세요! 무엇을 도와드릴까요?")

    if notice_store is None:
        DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
        notice_store = NoticeStore(DEFAULT_DB_PATH)

    register_notice_commands(app, notice_store)
    register_home_events(app, notice_store)

    return app


def main() -> None:
    settings = Settings.from_env()
    app = create_app(settings)
    handler = SocketModeHandler(app, settings.slack_app_token)
    handler.start()  # type: ignore[no-untyped-call]


if __name__ == "__main__":
    main()

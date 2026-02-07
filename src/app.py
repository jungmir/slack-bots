from __future__ import annotations

import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.context.ack import Ack
from slack_bolt.context.say import Say

from src.config import Settings


def create_app(settings: Settings, *, request_verification_enabled: bool = True) -> App:
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

    return app


def main() -> None:
    settings = Settings.from_env()
    app = create_app(settings)
    handler = SocketModeHandler(app, settings.slack_app_token)
    handler.start()  # type: ignore[no-untyped-call]


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from unittest.mock import patch

from slack_bolt import App, BoltRequest
from slack_sdk.web import SlackResponse

from src.app import create_app
from src.config import Settings

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


def _create_test_app() -> App:
    with patch("slack_sdk.web.client.WebClient.auth_test", return_value=_MOCK_AUTH_RESPONSE):
        return create_app(
            _make_settings(),
            request_verification_enabled=False,
        )


class TestPingCommand:
    def test_ping_responds_with_pong(self) -> None:
        app = _create_test_app()

        request = BoltRequest(
            body="command=%2Fping&text=&user_id=U1234",
            headers={
                "content-type": ["application/x-www-form-urlencoded"],
            },
        )
        response = app.dispatch(request)

        assert response.status == 200
        assert response.body is not None
        assert "pong" in response.body


class TestAppMention:
    def test_app_mention_responds(self) -> None:
        app = _create_test_app()

        event_payload = {
            "token": "test-token",
            "team_id": "T1234",
            "event": {
                "type": "app_mention",
                "user": "U1234",
                "text": "<@U0000> hello",
                "ts": "1234567890.123456",
                "channel": "C1234",
            },
            "type": "event_callback",
            "event_id": "Ev1234",
            "event_time": 1234567890,
        }

        request = BoltRequest(
            body=json.dumps(event_payload),
            headers={
                "content-type": ["application/json"],
            },
        )
        response = app.dispatch(request)

        assert response.status == 200

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import sentry_sdk
import structlog
from slack_bolt.middleware import Middleware
from slack_bolt.request import BoltRequest
from slack_bolt.response import BoltResponse

logger = structlog.get_logger()


def _extract_context(body: dict[str, Any]) -> dict[str, str]:
    """Extract identifying context from a Slack event payload."""
    event: dict[str, Any] = body.get("event", {})
    user_obj: dict[str, Any] = body.get("user", {})

    user_id = str(body.get("user_id") or event.get("user") or user_obj.get("id") or "")
    channel_id = str(body.get("channel_id") or event.get("channel") or "")
    command = str(body.get("command", ""))
    event_type = str(event.get("type", ""))
    action_type = str(body.get("type", ""))

    return {
        "slack_user_id": user_id,
        "channel_id": channel_id,
        "command": command,
        "event_type": event_type,
        "action_type": action_type,
    }


class RequestLoggingMiddleware(Middleware):
    """Bolt middleware that binds request context to every log line.

    For each incoming Slack request:
    1. Generates a unique ``request_id`` (UUID4).
    2. Extracts ``user_id``, ``channel_id``, ``command``, ``event_type``.
    3. Binds them to *structlog* contextvars so all downstream loggers
       automatically include these fields.
    4. Sets Sentry scope tags for error correlation.
    """

    def process(
        self,
        *,
        req: BoltRequest,
        resp: BoltResponse,
        next: Callable[[], BoltResponse],  # noqa: A002
    ) -> BoltResponse | None:
        request_id = str(uuid.uuid4())

        ctx = _extract_context(req.body if isinstance(req.body, dict) else {})

        # Bind to structlog contextvars — all subsequent log calls include these
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, **ctx)

        # Set Sentry scope so errors are tagged with the same context
        scope = sentry_sdk.get_current_scope()
        scope.set_tag("request_id", request_id)
        scope.set_tag("command", ctx["command"])
        scope.set_tag("event_type", ctx["event_type"])
        if ctx["slack_user_id"]:
            scope.set_user({"id": ctx["slack_user_id"]})

        logger.info("request_started")

        try:
            result = next()
        except Exception:
            logger.exception("request_failed")
            raise
        else:
            logger.info("request_completed")
            return result

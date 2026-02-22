from __future__ import annotations

import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.types import Event


def setup_sentry(
    *,
    dsn: str,
    environment: str = "dev",
    traces_sample_rate: float = 0.1,
) -> None:
    """Initialize Sentry error tracking.

    Does nothing when *dsn* is empty, so local development
    works without a Sentry project.

    Args:
        dsn: Sentry DSN. Empty string disables Sentry.
        environment: Deployment environment tag (dev / staging / production).
        traces_sample_rate: Fraction of transactions sent for performance monitoring.
    """
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        integrations=[
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        before_send=_before_send,
    )


def _before_send(
    event: Event,
    hint: dict[str, Any],
) -> Event | None:
    """Pre-processing hook before sending events to Sentry.

    Use this to scrub PII or filter noisy errors.
    """
    return event

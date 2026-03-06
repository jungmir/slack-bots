from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    slack_bot_token: str
    slack_app_token: str
    slack_signing_secret: str
    log_level: str = "INFO"
    log_json: bool = True
    sentry_dsn: str = ""
    sentry_environment: str = "dev"
    sentry_traces_sample_rate: float = 0.1
    dooray_api_token: str = ""
    dooray_project_id: str = ""
    healthcheck_port: int = 8080
    data_dir: str = "data"

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        slack_bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
        slack_app_token = os.environ.get("SLACK_APP_TOKEN", "")
        slack_signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")
        log_level = os.environ.get("LOG_LEVEL", "INFO")
        log_json = os.environ.get("LOG_JSON", "true").lower() in ("true", "1", "yes")
        sentry_dsn = os.environ.get("SENTRY_DSN", "")
        sentry_environment = os.environ.get("SENTRY_ENVIRONMENT", "dev")
        sentry_traces_sample_rate = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
        dooray_api_token = os.environ.get("DOORAY_API_TOKEN", "")
        dooray_project_id = os.environ.get("DOORAY_PROJECT_ID", "")
        healthcheck_port = int(os.environ.get("HEALTHCHECK_PORT", "8080"))
        data_dir = os.environ.get("DATA_DIR", "data")

        missing: list[str] = []
        if not slack_bot_token:
            missing.append("SLACK_BOT_TOKEN")
        if not slack_app_token:
            missing.append("SLACK_APP_TOKEN")
        if not slack_signing_secret:
            missing.append("SLACK_SIGNING_SECRET")

        if missing:
            msg = f"Missing required environment variables: {', '.join(missing)}"
            raise ValueError(msg)

        return cls(
            slack_bot_token=slack_bot_token,
            slack_app_token=slack_app_token,
            slack_signing_secret=slack_signing_secret,
            log_level=log_level,
            log_json=log_json,
            sentry_dsn=sentry_dsn,
            sentry_environment=sentry_environment,
            sentry_traces_sample_rate=sentry_traces_sample_rate,
            dooray_api_token=dooray_api_token,
            dooray_project_id=dooray_project_id,
            healthcheck_port=healthcheck_port,
            data_dir=data_dir,
        )

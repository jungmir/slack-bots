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
    dooray_api_token: str = ""
    dooray_project_id: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        slack_bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
        slack_app_token = os.environ.get("SLACK_APP_TOKEN", "")
        slack_signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")
        log_level = os.environ.get("LOG_LEVEL", "INFO")
        dooray_api_token = os.environ.get("DOORAY_API_TOKEN", "")
        dooray_project_id = os.environ.get("DOORAY_PROJECT_ID", "")

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
            dooray_api_token=dooray_api_token,
            dooray_project_id=dooray_project_id,
        )

"""Slack client and event handlers setup."""
from slack_bolt.async_app import AsyncApp
from app.config import settings


# Initialize Slack app
slack_app = AsyncApp(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
)


def get_slack_client():
    """Get Slack client instance."""
    return slack_app.client

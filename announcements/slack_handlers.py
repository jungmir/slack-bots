"""Slack Bolt handlers for Django."""
from slack_bolt import App
from django.conf import settings
from .models import Announcement, ReadReceipt, BlockKitTemplate

# Initialize Slack app
slack_app = App(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
    process_before_response=True,
)


# Import handlers from old codebase and adapt them
# Copy handlers from app_old/handlers/ and convert to use Django ORM

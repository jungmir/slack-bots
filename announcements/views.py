"""Django views for Slack events."""

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from slack_bolt.adapter.django import SlackRequestHandler
from .slack_handlers import slack_app

handler = SlackRequestHandler(slack_app)


@csrf_exempt
@require_POST
def slack_events(request):
    """Handle all Slack events and interactions."""
    return handler.handle(request)

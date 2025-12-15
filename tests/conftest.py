"""Pytest configuration and fixtures."""
import pytest
import os

# Set test environment variables
os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token"
os.environ["SLACK_SIGNING_SECRET"] = "test-secret"
os.environ["SLACK_APP_TOKEN"] = "xapp-test-token"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

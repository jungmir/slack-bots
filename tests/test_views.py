"""Tests for view builders."""
import pytest
from datetime import datetime
from app.views.home import build_home_view
from app.views.modals import build_announcement_modal, build_announcement_details_modal
from app.views.blocks import build_announcement_message
from app.models import Announcement


def test_build_home_view_empty():
    """Test building home view with no announcements."""
    view = build_home_view([], "U12345")

    assert view["type"] == "home"
    assert len(view["blocks"]) > 0
    assert any(block.get("type") == "header" for block in view["blocks"])


def test_build_home_view_with_announcements():
    """Test building home view with announcements."""
    announcements = [
        {
            "id": 1,
            "title": "Test Announcement",
            "channel_name": "general",
            "read_count": 5,
            "created_at": datetime(2024, 1, 1, 12, 0),
            "message_ts": "1234567890.123456",
            "channel_id": "C12345"
        }
    ]

    view = build_home_view(announcements, "U12345")

    assert view["type"] == "home"
    assert len(view["blocks"]) > 0

    # Check if announcement is in the view
    text_blocks = [
        block for block in view["blocks"]
        if block.get("type") == "section" and "text" in block
    ]
    announcement_found = any(
        "Test Announcement" in block["text"].get("text", "")
        for block in text_blocks
    )
    assert announcement_found


def test_build_announcement_modal():
    """Test building announcement creation modal."""
    modal = build_announcement_modal()

    assert modal["type"] == "modal"
    assert modal["callback_id"] == "announcement_modal"
    assert len(modal["blocks"]) == 3  # channel, title, content

    # Check for required inputs
    block_ids = [block["block_id"] for block in modal["blocks"]]
    assert "channel_select_block" in block_ids
    assert "title_block" in block_ids
    assert "content_block" in block_ids


def test_build_announcement_message():
    """Test building announcement message blocks."""
    blocks = build_announcement_message("Test Title", "Test Content")

    assert len(blocks) > 0
    assert blocks[0]["type"] == "header"
    assert "Test Title" in blocks[0]["text"]["text"]

    # Check for confirm button
    action_blocks = [block for block in blocks if block.get("type") == "actions"]
    assert len(action_blocks) > 0

    button = action_blocks[0]["elements"][0]
    assert button["type"] == "button"
    assert button["action_id"] == "confirm_announcement"


def test_build_announcement_details_modal():
    """Test building announcement details modal."""
    # Create a mock announcement
    class MockAnnouncement:
        title = "Test Announcement"
        channel_name = "general"
        content = "This is test content"
        created_at = datetime(2024, 1, 1, 12, 0)

    announcement = MockAnnouncement()
    read_users = ["• <@U12345> - 2024-01-01 12:00"]

    modal = build_announcement_details_modal(announcement, read_users)

    assert modal["type"] == "modal"
    assert len(modal["blocks"]) > 0

    # Check that announcement details are present
    text_blocks = [
        block for block in modal["blocks"]
        if block.get("type") == "section" and "text" in block
    ]
    content_found = any(
        "This is test content" in block["text"].get("text", "")
        for block in text_blocks
    )
    assert content_found

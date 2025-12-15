"""Modal submission handlers."""
from slack_bolt.async_app import AsyncApp
from sqlalchemy import select
from app.slack_client import slack_app, get_slack_client
from app.database import SessionLocal
from app.models import Announcement
from app.views.blocks import build_announcement_message


def save_announcement_to_db(channel_id, channel_name, title, content, sender_id, message_ts):
    """Save announcement to database."""
    with SessionLocal() as session:
        announcement = Announcement(
            channel_id=channel_id,
            channel_name=channel_name,
            title=title,
            content=content,
            sender_id=sender_id,
            message_ts=message_ts
        )
        session.add(announcement)
        session.commit()


@slack_app.view("announcement_modal")
async def handle_announcement_submission(ack, body, client, view):
    """Handle announcement modal submission."""
    # Acknowledge immediately
    await ack()

    # Extract form values
    values = view["state"]["values"]

    # Get channel selection
    channel_block = values["channel_select_block"]["channel_select"]
    channel_id = channel_block["selected_channel"]

    # Get title
    title = values["title_block"]["title_input"]["value"]

    # Get content
    content = values["content_block"]["content_input"]["value"]

    # Get sender info
    sender_id = body["user"]["id"]

    # Get channel info
    channel_info = await client.conversations_info(channel=channel_id)
    channel_name = channel_info["channel"]["name"]

    # Try to join the channel if it's a public channel
    try:
        await client.conversations_join(channel=channel_id)
    except Exception as e:
        # If join fails (e.g., private channel), the bot needs to be invited
        # Log the error but continue - it might already be a member
        print(f"Could not join channel {channel_id}: {e}")

    # Post announcement message to channel
    message_blocks = build_announcement_message(title, content)

    result = await client.chat_postMessage(
        channel=channel_id,
        blocks=message_blocks,
        text=f"New Announcement: {title}"
    )

    message_ts = result["ts"]

    # Save announcement to database
    try:
        save_announcement_to_db(
            channel_id=channel_id,
            channel_name=channel_name,
            title=title,
            content=content,
            sender_id=sender_id,
            message_ts=message_ts
        )
    except Exception as e:
        print(f"Error saving announcement to database: {e}")
        # Continue even if database save fails

    # Send confirmation DM to sender
    await client.chat_postMessage(
        channel=sender_id,
        text=f"✓ Your announcement '{title}' has been posted to #{channel_name}"
    )

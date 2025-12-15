"""App Home view handlers."""
from slack_bolt.async_app import AsyncApp
from sqlalchemy import select
from app.slack_client import slack_app
from app.database import AsyncSessionLocal
from app.models import Announcement, ReadReceipt
from app.views.home import build_home_view


@slack_app.event("app_home_opened")
async def handle_app_home_opened(event, client):
    """Handle App Home opened event."""
    user_id = event["user"]

    # Fetch announcements with read receipt counts
    async with AsyncSessionLocal() as session:
        # Get all announcements ordered by created_at desc
        result = await session.execute(
            select(Announcement).order_by(Announcement.created_at.desc())
        )
        announcements = result.scalars().all()

        # Build announcement data with read/unread counts
        announcement_data = []
        for ann in announcements:
            # Count read receipts
            read_count = len(ann.read_receipts)

            # Get channel member count (simplified - in production, use conversations.members)
            # For now, we'll use the read receipts to estimate unread count
            announcement_data.append({
                "id": ann.id,
                "title": ann.title,
                "channel_name": ann.channel_name,
                "read_count": read_count,
                "created_at": ann.created_at,
                "message_ts": ann.message_ts,
                "channel_id": ann.channel_id,
            })

    # Build and publish home view
    home_view = build_home_view(announcement_data, user_id)

    await client.views_publish(
        user_id=user_id,
        view=home_view
    )


@slack_app.action("create_announcement_button")
async def handle_create_announcement(ack, body, client):
    """Handle 'Create Announcement' button click."""
    await ack()

    from app.views.modals import build_announcement_modal

    # Open announcement creation modal
    await client.views_open(
        trigger_id=body["trigger_id"],
        view=build_announcement_modal()
    )


@slack_app.action("view_announcement_details")
async def handle_view_announcement_details(ack, body, client, action):
    """Handle viewing announcement details."""
    await ack()

    announcement_id = int(action["value"])

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Announcement).where(Announcement.id == announcement_id)
        )
        announcement = result.scalar_one_or_none()

        if not announcement:
            return

        # Get read and unread users
        read_users = [
            f"• <@{receipt.user_id}> - {receipt.confirmed_at.strftime('%Y-%m-%d %H:%M')}"
            for receipt in announcement.read_receipts
        ]

        # Build details view
        from app.views.modals import build_announcement_details_modal
        modal = build_announcement_details_modal(
            announcement,
            read_users
        )

        await client.views_open(
            trigger_id=body["trigger_id"],
            view=modal
        )


@slack_app.action("send_reminder")
async def handle_send_reminder(ack, body, action):
    """Handle sending reminder to unread users."""
    await ack()

    announcement_id = int(action["value"])

    from app.services.reminder import send_reminder_to_unread_users

    # Send reminders asynchronously
    await send_reminder_to_unread_users(announcement_id)

    # Update home view to show confirmation
    # (In production, you might want to show a toast notification)

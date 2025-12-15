"""Interactive action handlers."""
from slack_bolt.async_app import AsyncApp
from sqlalchemy import select
from app.slack_client import slack_app
from app.database import AsyncSessionLocal
from app.models import Announcement, ReadReceipt


@slack_app.action("confirm_announcement")
async def handle_confirm_announcement(ack, body, client, action):
    """Handle announcement confirmation button click."""
    await ack()

    # Extract announcement ID from action value
    message_ts = body["message"]["ts"]
    user_id = body["user"]["id"]

    # Get user info
    user_info = await client.users_info(user=user_id)
    user_name = user_info["user"]["real_name"] or user_info["user"]["name"]

    async with AsyncSessionLocal() as session:
        # Find announcement by message timestamp
        result = await session.execute(
            select(Announcement).where(Announcement.message_ts == message_ts)
        )
        announcement = result.scalar_one_or_none()

        if not announcement:
            await client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=user_id,
                text="⚠ Announcement not found in database."
            )
            return

        # Check if user already confirmed
        existing_receipt = await session.execute(
            select(ReadReceipt).where(
                ReadReceipt.announcement_id == announcement.id,
                ReadReceipt.user_id == user_id
            )
        )
        existing = existing_receipt.scalar_one_or_none()

        if existing:
            # Already confirmed
            await client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=user_id,
                text="✓ You have already confirmed this announcement."
            )
        else:
            # Create new read receipt
            receipt = ReadReceipt(
                announcement_id=announcement.id,
                user_id=user_id,
                user_name=user_name
            )
            session.add(receipt)
            await session.commit()

            # Send confirmation
            await client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=user_id,
                text=f"✓ Thank you! You've confirmed reading: *{announcement.title}*"
            )

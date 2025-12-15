"""Reminder service for sending DMs to unread users."""
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Announcement, ReadReceipt
from app.slack_client import get_slack_client


async def send_reminder_to_unread_users(announcement_id: int) -> dict:
    """Send reminder DMs to users who haven't confirmed the announcement.

    Args:
        announcement_id: ID of the announcement

    Returns:
        Dictionary with success count and error count
    """
    client = get_slack_client()
    success_count = 0
    error_count = 0

    async with AsyncSessionLocal() as session:
        # Get announcement
        result = await session.execute(
            select(Announcement).where(Announcement.id == announcement_id)
        )
        announcement = result.scalar_one_or_none()

        if not announcement:
            return {"success": 0, "errors": 1, "message": "Announcement not found"}

        # Get all users in the channel
        try:
            # Get channel members
            members_response = await client.conversations_members(
                channel=announcement.channel_id
            )
            all_user_ids = set(members_response["members"])

            # Get users who already confirmed
            confirmed_user_ids = {receipt.user_id for receipt in announcement.read_receipts}

            # Calculate unread users
            unread_user_ids = all_user_ids - confirmed_user_ids

            # Send reminder DM to each unread user
            for user_id in unread_user_ids:
                try:
                    # Skip bots
                    user_info = await client.users_info(user=user_id)
                    if user_info["user"].get("is_bot", False):
                        continue

                    # Send reminder DM
                    await client.chat_postMessage(
                        channel=user_id,
                        text=f"🔔 Reminder: Please confirm the announcement",
                        blocks=[
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🔔 Announcement Reminder"
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": (
                                        f"You have an unconfirmed announcement in <#{announcement.channel_id}>:\n\n"
                                        f"*{announcement.title}*\n\n"
                                        f"{announcement.content[:500]}..."
                                    )
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"Please go to <#{announcement.channel_id}> and click the 'Confirm' button."
                                }
                            }
                        ]
                    )
                    success_count += 1
                except Exception as e:
                    print(f"Error sending reminder to {user_id}: {e}")
                    error_count += 1

        except Exception as e:
            print(f"Error fetching channel members: {e}")
            return {"success": 0, "errors": 1, "message": str(e)}

    return {
        "success": success_count,
        "errors": error_count,
        "message": f"Sent {success_count} reminders, {error_count} errors"
    }

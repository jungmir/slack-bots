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


# ============================================================================
# App Home Handlers
# ============================================================================


@slack_app.event("app_home_opened")
def handle_app_home_opened(event, client):
    """Handle App Home opened event."""
    user_id = event["user"]

    # Fetch announcements with Django ORM
    announcements = Announcement.objects.all()[:10]

    # Build announcement data
    announcement_data = []
    for ann in announcements:
        announcement_data.append(
            {
                "id": ann.id,
                "title": ann.title,
                "channel_name": ann.channel_name,
                "read_count": ann.read_count,
                "created_at": ann.created_at,
                "message_ts": ann.message_ts,
                "channel_id": ann.channel_id,
            }
        )

    # Try to get home template from database
    try:
        template = BlockKitTemplate.objects.filter(
            template_type="home", is_active=True
        ).first()

        if template:
            # Use template and inject dynamic data
            blocks = inject_dynamic_data_to_home(template.blocks, announcement_data)
        else:
            # Use default blocks
            blocks = build_home_view_blocks(announcement_data)
    except Exception as e:
        print(f"Error loading home template: {e}")
        blocks = build_home_view_blocks(announcement_data)

    client.views_publish(user_id=user_id, view={"type": "home", "blocks": blocks})


@slack_app.action("create_announcement_button")
def handle_create_announcement(ack, body, client):
    """Handle 'Create Announcement' button click."""
    ack()

    # Try to get modal template from database
    try:
        template = BlockKitTemplate.objects.get(
            template_type="modal", is_active=True, name="announcement_creation"
        )
        modal_blocks = template.blocks
    except BlockKitTemplate.DoesNotExist:
        # Fallback to default modal
        modal_blocks = build_announcement_modal_blocks()

    modal_view = {
        "type": "modal",
        "callback_id": "announcement_modal",
        "title": {"type": "plain_text", "text": "Create Announcement"},
        "submit": {"type": "plain_text", "text": "Send"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": modal_blocks,
    }

    client.views_open(trigger_id=body["trigger_id"], view=modal_view)


@slack_app.action("view_announcement_details")
def handle_view_announcement_details(ack, body, client, action):
    """Handle viewing announcement details."""
    ack()

    announcement_id = int(action["value"])

    try:
        announcement = Announcement.objects.get(id=announcement_id)

        # Get read users
        read_users = [
            f"• <@{receipt.user_id}> - {receipt.confirmed_at.strftime('%Y-%m-%d %H:%M')}"
            for receipt in announcement.read_receipts.all()
        ]

        # Build details modal
        modal = build_announcement_details_modal(announcement, read_users)

        client.views_open(trigger_id=body["trigger_id"], view=modal)
    except Announcement.DoesNotExist:
        pass


@slack_app.action("send_reminder")
def handle_send_reminder(ack, body, action, client):
    """Handle sending reminder to unread users."""
    ack()

    announcement_id = int(action["value"])

    try:
        announcement = Announcement.objects.get(id=announcement_id)

        # Get channel members
        members_response = client.conversations_members(channel=announcement.channel_id)
        all_user_ids = set(members_response["members"])

        # Get confirmed user IDs
        confirmed_user_ids = set(
            announcement.read_receipts.values_list("user_id", flat=True)
        )

        # Get unread users
        unread_user_ids = all_user_ids - confirmed_user_ids

        # Send reminders
        for user_id in unread_user_ids:
            try:
                user_info = client.users_info(user=user_id)
                if user_info["user"].get("is_bot", False):
                    continue

                client.chat_postMessage(
                    channel=user_id,
                    text=f"🔔 Reminder: Please confirm the announcement",
                    blocks=[
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": "🔔 Announcement Reminder",
                            },
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"You have an unconfirmed announcement in <#{announcement.channel_id}>:\n\n"
                                    f"*{announcement.title}*\n\n"
                                    f"{announcement.content[:500]}..."
                                ),
                            },
                        },
                    ],
                )
            except Exception as e:
                print(f"Error sending reminder to {user_id}: {e}")

    except Announcement.DoesNotExist:
        pass


# ============================================================================
# Modal Handlers
# ============================================================================


@slack_app.view("announcement_modal")
def handle_announcement_submission(ack, body, client, view):
    """Handle announcement modal submission."""
    ack()

    values = view["state"]["values"]

    # Extract values
    channel_id = values["channel_select_block"]["channel_select"]["selected_channel"]
    title = values["title_block"]["title_input"]["value"]
    content = values["content_block"]["content_input"]["value"]
    sender_id = body["user"]["id"]

    # Get channel info
    channel_info = client.conversations_info(channel=channel_id)
    channel_name = channel_info["channel"]["name"]

    # Try to join channel
    try:
        client.conversations_join(channel=channel_id)
    except Exception as e:
        print(f"Could not join channel {channel_id}: {e}")

    # Get announcement message blocks
    try:
        template = BlockKitTemplate.objects.filter(
            template_type="announcement", is_active=True
        ).first()

        if template:
            message_blocks = template.blocks
            # Simple template variable replacement
            import json

            blocks_json = json.dumps(message_blocks)
            blocks_json = blocks_json.replace("{title}", title).replace(
                "{content}", content
            )
            message_blocks = json.loads(blocks_json)
        else:
            message_blocks = build_announcement_message_blocks(title, content)
    except Exception:
        message_blocks = build_announcement_message_blocks(title, content)

    # Post message
    result = client.chat_postMessage(
        channel=channel_id, blocks=message_blocks, text=f"New Announcement: {title}"
    )

    # Save to database
    Announcement.objects.create(
        channel_id=channel_id,
        channel_name=channel_name,
        title=title,
        content=content,
        sender_id=sender_id,
        message_ts=result["ts"],
    )

    # Send confirmation DM
    client.chat_postMessage(
        channel=sender_id,
        text=f"✓ Your announcement '{title}' has been posted to #{channel_name}",
    )


# ============================================================================
# Action Handlers
# ============================================================================


@slack_app.action("confirm_announcement")
def handle_confirm_announcement(ack, body, client, action):
    """Handle announcement confirmation button click."""
    ack()

    message_ts = body["message"]["ts"]
    user_id = body["user"]["id"]

    # Get user info
    user_info = client.users_info(user=user_id)
    user_name = user_info["user"]["real_name"] or user_info["user"]["name"]

    try:
        announcement = Announcement.objects.get(message_ts=message_ts)

        # Check if already confirmed
        if ReadReceipt.objects.filter(
            announcement=announcement, user_id=user_id
        ).exists():
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=user_id,
                text="✓ You have already confirmed this announcement.",
            )
        else:
            # Create read receipt
            ReadReceipt.objects.create(
                announcement=announcement, user_id=user_id, user_name=user_name
            )
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=user_id,
                text=f"✓ Thank you! You've confirmed reading: *{announcement.title}*",
            )
    except Announcement.DoesNotExist:
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=user_id,
            text="⚠ Announcement not found in database.",
        )


# ============================================================================
# Helper Functions for Building Blocks
# ============================================================================


def build_home_view_blocks(announcements):
    """Build App Home view blocks."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📢 Announcement Manager"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Send announcements to channels and track who has read them.",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "➕ Create Announcement"},
                    "style": "primary",
                    "action_id": "create_announcement_button",
                }
            ],
        },
        {"type": "divider"},
    ]

    if announcements:
        blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Recent Announcements"},
            }
        )

        for ann in announcements:
            blocks.extend(
                [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*{ann['title']}*\n"
                                f"Channel: #{ann['channel_name']}\n"
                                f"Created: {ann['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
                                f"✓ {ann['read_count']} confirmed"
                            ),
                        },
                        "accessory": {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Details"},
                            "action_id": "view_announcement_details",
                            "value": str(ann["id"]),
                        },
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🔔 Send Reminder",
                                },
                                "action_id": "send_reminder",
                                "value": str(ann["id"]),
                            }
                        ],
                    },
                    {"type": "divider"},
                ]
            )
    else:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_No announcements yet. Click 'Create Announcement' to get started!_",
                },
            }
        )

    return blocks


def build_announcement_modal_blocks():
    """Build announcement creation modal blocks."""
    return [
        {
            "type": "input",
            "block_id": "channel_select_block",
            "element": {
                "type": "channels_select",
                "placeholder": {"type": "plain_text", "text": "Select a channel"},
                "action_id": "channel_select",
            },
            "label": {"type": "plain_text", "text": "Channel"},
        },
        {
            "type": "input",
            "block_id": "title_block",
            "element": {
                "type": "plain_text_input",
                "action_id": "title_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Enter announcement title",
                },
                "max_length": 200,
            },
            "label": {"type": "plain_text", "text": "Title"},
        },
        {
            "type": "input",
            "block_id": "content_block",
            "element": {
                "type": "plain_text_input",
                "action_id": "content_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "Enter announcement content",
                },
                "max_length": 3000,
            },
            "label": {"type": "plain_text", "text": "Content"},
        },
    ]


def build_announcement_message_blocks(title, content):
    """Build announcement message blocks."""
    return [
        {"type": "header", "text": {"type": "plain_text", "text": f"📢 {title}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": content}},
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✓ Confirm"},
                    "style": "primary",
                    "action_id": "confirm_announcement",
                }
            ],
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "_Click 'Confirm' to acknowledge you've read this announcement._",
                }
            ],
        },
    ]


def build_announcement_details_modal(announcement, read_users):
    """Build announcement details modal."""
    read_list = "\n".join(read_users) if read_users else "_No confirmations yet_"

    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Announcement Details"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": announcement.title},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Channel:* #{announcement.channel_name}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Created:* {announcement.created_at.strftime('%Y-%m-%d %H:%M')}",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Content:*\n{announcement.content}",
                },
            },
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"✓ Confirmed ({len(read_users)})",
                },
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": read_list}},
        ],
    }


def inject_dynamic_data_to_home(template_blocks, announcements):
    """
    Inject dynamic announcement data into home template blocks.

    Template should contain a placeholder block with special marker:
    {"type": "section", "block_id": "__ANNOUNCEMENTS_LIST__"}

    This will be replaced with actual announcement blocks.
    """
    import copy

    blocks = copy.deepcopy(template_blocks)

    # Find the announcements list placeholder
    announcement_insert_index = None
    for i, block in enumerate(blocks):
        if block.get("block_id") == "__ANNOUNCEMENTS_LIST__":
            announcement_insert_index = i
            break

    # If placeholder found, replace with actual announcements
    if announcement_insert_index is not None:
        # Remove placeholder
        blocks.pop(announcement_insert_index)

        # Insert announcement blocks
        if announcements:
            announcement_blocks = []
            for ann in announcements:
                announcement_blocks.extend(
                    [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*{ann['title']}*\n"
                                    f"Channel: #{ann['channel_name']}\n"
                                    f"Created: {ann['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
                                    f"✓ {ann['read_count']} confirmed"
                                ),
                            },
                            "accessory": {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View Details"},
                                "action_id": "view_announcement_details",
                                "value": str(ann["id"]),
                            },
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "🔔 Send Reminder",
                                    },
                                    "action_id": "send_reminder",
                                    "value": str(ann["id"]),
                                }
                            ],
                        },
                        {"type": "divider"},
                    ]
                )

            # Insert at the placeholder position
            for block in reversed(announcement_blocks):
                blocks.insert(announcement_insert_index, block)
        else:
            # No announcements, insert empty message
            blocks.insert(
                announcement_insert_index,
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "_No announcements yet. Click 'Create Announcement' to get started!_",
                    },
                },
            )

    return blocks

"""App Home view builder."""


def build_home_view(announcements: list, user_id: str) -> dict:
    """Build the App Home view with announcement dashboard.

    Args:
        announcements: List of announcement data dictionaries
        user_id: Current user's Slack ID

    Returns:
        Slack view object
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📢 Announcement Manager"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Send announcements to channels and track who has read them."
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "➕ Create Announcement"
                    },
                    "style": "primary",
                    "action_id": "create_announcement_button"
                }
            ]
        },
        {
            "type": "divider"
        }
    ]

    # Add announcements section
    if announcements:
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Recent Announcements"
            }
        })

        for ann in announcements[:10]:  # Show max 10 recent announcements
            blocks.extend([
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{ann['title']}*\n"
                            f"Channel: #{ann['channel_name']}\n"
                            f"Created: {ann['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
                            f"✓ {ann['read_count']} confirmed"
                        )
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Details"
                        },
                        "action_id": "view_announcement_details",
                        "value": str(ann['id'])
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "🔔 Send Reminder"
                            },
                            "action_id": "send_reminder",
                            "value": str(ann['id'])
                        }
                    ]
                },
                {
                    "type": "divider"
                }
            ])
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_No announcements yet. Click 'Create Announcement' to get started!_"
            }
        })

    return {
        "type": "home",
        "blocks": blocks
    }

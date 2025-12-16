"""Slack Block Kit message builders."""


def build_announcement_message(title: str, content: str) -> list:
    """Build announcement message blocks.

    Args:
        title: Announcement title
        content: Announcement content

    Returns:
        List of Slack Block Kit blocks
    """
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📢 {title}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": content
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✓ Confirm"
                    },
                    "style": "primary",
                    "action_id": "confirm_announcement"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "_Click 'Confirm' to acknowledge you've read this announcement._"
                }
            ]
        }
    ]

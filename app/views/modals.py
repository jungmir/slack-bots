"""Modal view builders."""


def build_announcement_modal() -> dict:
    """Build the announcement creation modal.

    Returns:
        Slack modal view object
    """
    return {
        "type": "modal",
        "callback_id": "announcement_modal",
        "title": {
            "type": "plain_text",
            "text": "Create Announcement"
        },
        "submit": {
            "type": "plain_text",
            "text": "Send"
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel"
        },
        "blocks": [
            {
                "type": "input",
                "block_id": "channel_select_block",
                "element": {
                    "type": "channels_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a channel"
                    },
                    "action_id": "channel_select"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Channel"
                }
            },
            {
                "type": "input",
                "block_id": "title_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "title_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter announcement title"
                    },
                    "max_length": 200
                },
                "label": {
                    "type": "plain_text",
                    "text": "Title"
                }
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
                        "text": "Enter announcement content"
                    },
                    "max_length": 3000
                },
                "label": {
                    "type": "plain_text",
                    "text": "Content"
                }
            }
        ]
    }


def build_announcement_details_modal(announcement, read_users: list) -> dict:
    """Build the announcement details modal.

    Args:
        announcement: Announcement model instance
        read_users: List of formatted read user strings

    Returns:
        Slack modal view object
    """
    read_list = "\n".join(read_users) if read_users else "_No confirmations yet_"

    return {
        "type": "modal",
        "title": {
            "type": "plain_text",
            "text": "Announcement Details"
        },
        "close": {
            "type": "plain_text",
            "text": "Close"
        },
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": announcement.title
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Channel:* #{announcement.channel_name}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Created:* {announcement.created_at.strftime('%Y-%m-%d %H:%M')}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Content:*\n{announcement.content}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"✓ Confirmed ({len(read_users)})"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": read_list
                }
            }
        ]
    }

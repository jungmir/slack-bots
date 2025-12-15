# Slack Announcement Bot

A Slack bot for managing announcements and reminders. Send announcements to channels, track read receipts, and send reminder DMs to users who haven't acknowledged announcements.

## Features

- 📢 **Create Announcements**: Send announcements to any channel with title and content
- ✓ **Read Receipt Tracking**: Track which users have confirmed reading announcements
- 📊 **Dashboard**: View all announcements with read/unread statistics
- 🔔 **Reminders**: Send DM reminders to users who haven't confirmed
- 🏠 **App Home**: Intuitive interface within Slack

## Tech Stack

- **Python 3.13.11**
- **FastAPI** - Modern async web framework
- **SQLAlchemy** - Async ORM with SQLite
- **Slack Bolt** - Slack app framework
- **uv** - Fast Python package manager

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd slack-bots
```

2. Install dependencies using uv:
```bash
uv sync --frozen
```

3. Copy the example environment file and configure:
```bash
cp .env.example .env
```

4. Edit `.env` with your Slack credentials:
```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token
```

## Slack App Setup

1. Create a new Slack App at [api.slack.com/apps](https://api.slack.com/apps)

2. Configure OAuth & Permissions with these scopes:
   - `chat:write` - Post messages
   - `im:write` - Send DMs
   - `channels:read` - List channels
   - `channels:join` - Join public channels
   - `users:read` - Get user information
   - `channels:history` - Read channel messages
   - `groups:read` - Access private channels info
   - `groups:write` - Manage private channels (optional)
   - `conversations.members:read` - Read channel members

3. Enable Event Subscriptions:
   - Request URL: `https://your-domain.com/slack/events`
   - Subscribe to: `app_home_opened`

4. Enable Interactivity:
   - Request URL: `https://your-domain.com/slack/interactions`

5. Enable App Home:
   - Home Tab: Enabled

6. Install the app to your workspace

## Running the Bot

Development mode:
```bash
uv run app.py
```

Production mode with uvicorn:
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 3000
```

## Running Tests

```bash
uv run pytest
```

Run with coverage:
```bash
uv run pytest --cov=app
```

## Project Structure

```
slack-bots/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── slack_client.py      # Slack Bolt app
│   ├── handlers/            # Event and action handlers
│   │   ├── home.py
│   │   ├── modals.py
│   │   └── actions.py
│   ├── views/               # Slack UI views
│   │   ├── home.py
│   │   ├── modals.py
│   │   └── blocks.py
│   └── services/            # Business logic
│       └── reminder.py
├── tests/                   # Test suite
├── app.py                   # Entry point
├── pyproject.toml           # Project dependencies
└── .env.example             # Environment template
```

## Usage

### Creating an Announcement

1. Open the Slack app and go to the Home tab
2. Click "Create Announcement" button
3. Select a channel, enter title and content
4. Click "Send"

### Confirming an Announcement

1. Users in the channel see the announcement with a "Confirm" button
2. Click "Confirm" to mark as read
3. Already confirmed users will see "You have already confirmed this announcement"

### Viewing Read Status

1. Go to the App Home tab
2. View list of announcements with read counts
3. Click "View Details" to see who has confirmed

### Sending Reminders

1. Go to the App Home tab
2. Click "Send Reminder" on any announcement
3. DMs will be sent to all users who haven't confirmed

## License

MIT

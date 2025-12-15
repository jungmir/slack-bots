# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Slack bot for managing announcements and reminders. Users can send announcements to channels, track read receipts, and send reminder DMs to users who haven't acknowledged the announcement.

**Reference:** This project is inspired by the Bulksend bot (App ID: A07D54UCXR7).

## Getting Started

**Python 3.13.11** with **uv** package manager:
- `uv sync --frozen` - Install dependencies
- `uv run app.py` - Run the bot
- `uv run pytest` - Run tests

## Core Features

### 1. Announcement Creation
- User clicks "Send Announcement" button in Slack App Home
- Modal form collects:
  - Target channel
  - Announcement title
  - Announcement content
- Submitting the form posts announcement to the selected channel

### 2. Announcement Message Format
Each announcement message contains:
- Title (heading)
- Content (body text)
- "Confirm" button for acknowledgment

### 3. Read Receipt Tracking
- Unread users: Clicking "Confirm" marks announcement as read
- Already read users: Clicking "Confirm" shows "Already confirmed" message
- System tracks read/unread status per user

### 4. Announcement Dashboard
- Available in App Home
- Shows list of sent announcements
- Displays read vs. unread user lists for each announcement
- Allows sending reminder DMs to unread users

### 5. Reminder System
- Send reminder DMs to users who haven't confirmed
- Reminders sent on-demand from dashboard

## Architecture

### Key Components

**App Home:**
- "Send Announcement" button
- Announcement dashboard with read/unread tracking
- Reminder controls

**Modals:**
- Announcement creation form (channel selector, title input, content textarea)

**Interactive Components:**
- "Confirm" button on announcement messages
- Action handlers for button interactions

**State Management:**
- User read/unread status per announcement
- Announcement metadata (channel, timestamp, sender, content)
- Database or persistent storage for tracking

**Background Jobs:**
- Reminder DM dispatch
- Status updates on button clicks

### Event Handling
- `app_home_opened` - Display dashboard
- `view_submission` - Handle announcement modal submission
- `block_actions` - Handle "Confirm" button clicks
- Message posting via `chat.postMessage`
- DM sending via `chat.postMessage` to user IDs

## Configuration

Required Slack App credentials:
- **Bot Token** (`SLACK_BOT_TOKEN`) - For posting messages and reading channels
- **Signing Secret** (`SLACK_SIGNING_SECRET`) - For verifying requests
- **App Token** (`SLACK_APP_TOKEN`) - For Socket Mode (if used)

Required Slack App Scopes:
- `chat:write` - Post messages to channels
- `im:write` - Send DMs
- `channels:read` - List channels for selection
- `channels:join` - Join public channels automatically
- `channels:history` - Read channel messages
- `users:read` - Get user information
- `conversations.members:read` - Read channel members for reminder functionality
- `groups:read` - Access private channels info (optional)
- `groups:write` - Manage private channels (optional)

Database/Storage:
- Store announcement records (id, channel, title, content, timestamp, sender)
- Store read receipts (announcement_id, user_id, confirmed_at)

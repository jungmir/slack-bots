"""Main FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from app.config import settings
from app.database import init_db
from app.slack_client import slack_app
from app import handlers  # noqa: F401 - Import to register handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="Slack Announcement Bot",
    description="Bot for managing announcements and reminders",
    version="0.1.0",
    lifespan=lifespan,
)

# Create Slack request handler
slack_handler = AsyncSlackRequestHandler(slack_app)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/slack/events")
async def slack_events(request: Request):
    """Handle Slack events."""
    return await slack_handler.handle(request)


@app.post("/slack/interactions")
async def slack_interactions(request: Request):
    """Handle Slack interactive components."""
    return await slack_handler.handle(request)

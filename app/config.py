"""Application configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Slack credentials
    SLACK_BOT_TOKEN: str
    SLACK_SIGNING_SECRET: str
    SLACK_APP_TOKEN: str = ""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./announcements.db"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 3000
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

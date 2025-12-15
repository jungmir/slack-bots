"""Database utility functions to wrap async operations."""
import asyncio
from functools import wraps
from app.database import AsyncSessionLocal


def run_async_db_operation(func):
    """Decorator to safely run async database operations."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            print(f"Database operation error: {e}")
            raise
    return wrapper


async def get_session():
    """Get a new database session."""
    async with AsyncSessionLocal() as session:
        return session

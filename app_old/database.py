"""Database configuration and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from app.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Convert async URL to sync URL for SQLite
database_url = settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///")

# Create sync engine
engine = create_engine(
    database_url,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
    pool_pre_ping=True,
)

# Create sync session factory
SessionLocal = sessionmaker(
    engine,
    class_=Session,
    expire_on_commit=False,
)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

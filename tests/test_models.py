"""Tests for database models."""
import pytest
from datetime import datetime
from sqlalchemy import select
from app.models import Announcement, ReadReceipt
from app.database import Base, engine, AsyncSessionLocal


@pytest.fixture(scope="function")
async def setup_database():
    """Create tables before each test and drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_create_announcement(setup_database):
    """Test creating an announcement."""
    async with AsyncSessionLocal() as session:
        announcement = Announcement(
            channel_id="C12345",
            channel_name="general",
            title="Test Announcement",
            content="This is a test announcement",
            sender_id="U12345",
            message_ts="1234567890.123456"
        )
        session.add(announcement)
        await session.commit()

        # Query back
        result = await session.execute(select(Announcement))
        saved_announcement = result.scalar_one()

        assert saved_announcement.title == "Test Announcement"
        assert saved_announcement.channel_name == "general"
        assert saved_announcement.content == "This is a test announcement"


@pytest.mark.asyncio
async def test_create_read_receipt(setup_database):
    """Test creating a read receipt."""
    async with AsyncSessionLocal() as session:
        # Create announcement first
        announcement = Announcement(
            channel_id="C12345",
            channel_name="general",
            title="Test Announcement",
            content="This is a test",
            sender_id="U12345",
            message_ts="1234567890.123456"
        )
        session.add(announcement)
        await session.commit()

        # Create read receipt
        receipt = ReadReceipt(
            announcement_id=announcement.id,
            user_id="U67890",
            user_name="Test User"
        )
        session.add(receipt)
        await session.commit()

        # Query back
        result = await session.execute(
            select(ReadReceipt).where(ReadReceipt.announcement_id == announcement.id)
        )
        saved_receipt = result.scalar_one()

        assert saved_receipt.user_id == "U67890"
        assert saved_receipt.user_name == "Test User"
        assert saved_receipt.announcement_id == announcement.id


@pytest.mark.asyncio
async def test_announcement_read_receipts_relationship(setup_database):
    """Test the relationship between announcements and read receipts."""
    async with AsyncSessionLocal() as session:
        # Create announcement
        announcement = Announcement(
            channel_id="C12345",
            channel_name="general",
            title="Test Announcement",
            content="This is a test",
            sender_id="U12345",
            message_ts="1234567890.123456"
        )
        session.add(announcement)
        await session.commit()

        # Add multiple read receipts
        for i in range(3):
            receipt = ReadReceipt(
                announcement_id=announcement.id,
                user_id=f"U{i}",
                user_name=f"User {i}"
            )
            session.add(receipt)
        await session.commit()

        # Query announcement with receipts
        result = await session.execute(
            select(Announcement).where(Announcement.id == announcement.id)
        )
        saved_announcement = result.scalar_one()

        assert len(saved_announcement.read_receipts) == 3
        assert all(receipt.announcement_id == announcement.id for receipt in saved_announcement.read_receipts)


@pytest.mark.asyncio
async def test_unique_user_announcement_constraint(setup_database):
    """Test that the same user cannot confirm the same announcement twice."""
    async with AsyncSessionLocal() as session:
        # Create announcement
        announcement = Announcement(
            channel_id="C12345",
            channel_name="general",
            title="Test",
            content="Test",
            sender_id="U12345",
            message_ts="1234567890.123456"
        )
        session.add(announcement)
        await session.commit()

        # Add first receipt
        receipt1 = ReadReceipt(
            announcement_id=announcement.id,
            user_id="U67890",
            user_name="Test User"
        )
        session.add(receipt1)
        await session.commit()

        # Try to add duplicate - should raise error
        receipt2 = ReadReceipt(
            announcement_id=announcement.id,
            user_id="U67890",  # Same user
            user_name="Test User"
        )
        session.add(receipt2)

        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            await session.commit()

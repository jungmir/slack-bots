"""Database models for announcements and read receipts."""
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Announcement(Base):
    """Model for storing announcements."""
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(50), nullable=False)
    channel_name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sender_id: Mapped[str] = mapped_column(String(50), nullable=False)
    message_ts: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationship to read receipts
    read_receipts: Mapped[list["ReadReceipt"]] = relationship(
        "ReadReceipt",
        back_populates="announcement",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Announcement(id={self.id}, title='{self.title}', channel='{self.channel_name}')>"


class ReadReceipt(Base):
    """Model for tracking read receipts."""
    __tablename__ = "read_receipts"
    __table_args__ = (
        UniqueConstraint('announcement_id', 'user_id', name='unique_user_announcement'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(
        ForeignKey("announcements.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(50), nullable=False)
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationship to announcement
    announcement: Mapped["Announcement"] = relationship(
        "Announcement",
        back_populates="read_receipts"
    )

    def __repr__(self):
        return f"<ReadReceipt(id={self.id}, user='{self.user_name}', announcement_id={self.announcement_id})>"

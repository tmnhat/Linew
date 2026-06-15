"""
Distribution models: DistributionLog và NewsletterSubscriber.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Boolean, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class DistributionLog(Base):
    __tablename__ = "distribution_logs"

    id: Mapped[str] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    article_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(255))
    external_url: Mapped[Optional[str]] = mapped_column(String(2048))
    error: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_dist_logs_channel_status", "channel", "status"),
        Index("idx_dist_logs_created", "created_at"),
        # Unique constraint: only one successful distribution per article per channel
        Index(
            "idx_dist_logs_unique_success",
            "article_id",
            "channel",
            postgresql_where=status == "success",
            unique=True,
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "article_id": str(self.article_id),
            "channel": self.channel,
            "status": self.status,
            "external_id": self.external_id,
            "external_url": self.external_url,
            "error": self.error,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id: Mapped[str] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    unsubscribed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    categories: Mapped[list] = mapped_column(JSONB, default=["tech", "finance"])
    frequency: Mapped[str] = mapped_column(String(20), default="daily")
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    total_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_opened: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_newsletter_active", "is_active", postgresql_where="is_active = true"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "is_active": self.is_active,
            "subscribed_at": self.subscribed_at.isoformat() if self.subscribed_at else None,
            "unsubscribed_at": self.unsubscribed_at.isoformat() if self.unsubscribed_at else None,
            "categories": self.categories,
            "frequency": self.frequency,
            "last_sent_at": self.last_sent_at.isoformat() if self.last_sent_at else None,
            "total_sent": self.total_sent,
            "total_opened": self.total_opened,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

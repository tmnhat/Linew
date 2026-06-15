"""
Source model for RSS feeds.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, Integer, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    feed_url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    site_url: Mapped[Optional[str]] = mapped_column(String(2048))
    category_hint: Mapped[Optional[str]] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(10), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    fetch_interval: Mapped[int] = mapped_column(Integer, default=30)
    crawl_difficulty: Mapped[str] = mapped_column(String(10), default="easy")
    requires_flaresolverr: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_proxy: Mapped[bool] = mapped_column(Boolean, default=False)
    is_paywall: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_headers: Mapped[Optional[dict]] = mapped_column(JSONB)
    content_selector: Mapped[Optional[str]] = mapped_column(String(255))
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    articles: Mapped[list["Article"]] = relationship("Article", back_populates="source")

    __table_args__ = (
        Index("idx_sources_active", "is_active", postgresql_where=is_active == True),  # noqa: E712
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "feed_url": self.feed_url,
            "site_url": self.site_url,
            "category_hint": self.category_hint,
            "language": self.language,
            "is_active": self.is_active,
            "fetch_interval": self.fetch_interval,
            "crawl_difficulty": self.crawl_difficulty,
            "requires_flaresolverr": self.requires_flaresolverr,
            "requires_proxy": self.requires_proxy,
            "is_paywall": self.is_paywall,
            "custom_headers": self.custom_headers,
            "content_selector": self.content_selector,
            "last_fetched_at": self.last_fetched_at.isoformat() if self.last_fetched_at else None,
            "last_error": self.last_error,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

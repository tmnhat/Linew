"""
RawSignal model - stores all crawled RSS items in their original form.
This is the "gold mine" for analytics - we save EVERYTHING, including duplicates.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Boolean, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RawSignal(Base):
    """Raw RSS signal - stores everything crawled before any processing."""
    __tablename__ = "raw_signals"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source reference
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))

    # Source metadata
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    feed_url: Mapped[Optional[str]] = mapped_column(String(2048))
    feed_title: Mapped[Optional[str]] = mapped_column(String(255))

    # Original data from RSS (NEVER modified)
    original_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    original_title: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_summary: Mapped[Optional[str]] = mapped_column(Text)
    original_content: Mapped[Optional[str]] = mapped_column(Text)
    original_html: Mapped[Optional[str]] = mapped_column(Text)
    original_image_url: Mapped[Optional[str]] = mapped_column(String(2048))
    original_author: Mapped[Optional[str]] = mapped_column(String(255))
    original_language: Mapped[Optional[str]] = mapped_column(String(10))
    original_tags: Mapped[list] = mapped_column(JSONB, default=list)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Hashing for dedup & tracking
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))

    # Content metrics
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    has_image: Mapped[bool] = mapped_column(Boolean, default=False)

    # Processing tracking
    was_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    article_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    processing_result: Mapped[Optional[str]] = mapped_column(String(30))
    processing_note: Mapped[Optional[str]] = mapped_column(Text)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Archive tracking
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_raw_signals_created", "created_at"),
        Index("idx_raw_signals_source", "source_id", "created_at"),
        Index("idx_raw_signals_processed", "was_processed", "created_at"),
        Index("idx_raw_signals_language", "original_language"),
        Index("idx_raw_signals_result", "processing_result"),
        Index("idx_raw_signals_archived", "is_archived"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "source_id": str(self.source_id) if self.source_id else None,
            "source_name": self.source_name,
            "feed_url": self.feed_url,
            "feed_title": self.feed_title,
            "original_url": self.original_url,
            "original_title": self.original_title,
            "original_summary": self.original_summary,
            "original_content": self.original_content,
            "original_html": self.original_html,
            "original_image_url": self.original_image_url,
            "original_author": self.original_author,
            "original_language": self.original_language,
            "original_tags": self.original_tags,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "url_hash": self.url_hash,
            "title_hash": self.title_hash,
            "content_hash": self.content_hash,
            "word_count": self.word_count,
            "has_image": self.has_image,
            "was_processed": self.was_processed,
            "article_id": str(self.article_id) if self.article_id else None,
            "processing_result": self.processing_result,
            "processing_note": self.processing_note,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "is_archived": self.is_archived,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_archive_tuple(self) -> tuple:
        """Convert to tuple for SQLite archive insertion."""
        import json
        return (
            str(self.id),
            str(self.source_id) if self.source_id else None,
            self.source_name,
            self.original_url,
            self.original_title,
            self.original_summary,
            self.original_content,
            self.original_html,
            self.original_image_url,
            self.original_author,
            self.original_language,
            json.dumps(self.original_tags) if self.original_tags else "[]",
            self.published_at.isoformat() if self.published_at else None,
            self.feed_url,
            self.feed_title,
            self.url_hash,
            self.title_hash,
            self.content_hash,
            self.word_count,
            self.has_image,
            self.was_processed,
            str(self.article_id) if self.article_id else None,
            self.processing_result,
            self.processing_note,
            self.processed_at.isoformat() if self.processed_at else None,
            self.created_at.isoformat() if self.created_at else None,
        )


def hash_url(url: str) -> str:
    """Normalize URL and return SHA-256 hash."""
    normalized = url.lower().strip()
    for prefix in ["http://", "https://"]:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    if normalized.endswith("/"):
        normalized = normalized[:-1]
    return hashlib.sha256(normalized.encode()).hexdigest()


def hash_title(title: str) -> str:
    """Normalize title and return SHA-256 hash."""
    normalized = title.lower().strip()
    normalized = " ".join(normalized.split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def hash_content(content: Optional[str]) -> Optional[str]:
    """Return SHA-256 hash of content."""
    if not content:
        return None
    return hashlib.sha256(content.encode()).hexdigest()

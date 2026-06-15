"""
Article model and state machine.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, DateTime,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base


class ArticleState(str, enum.Enum):
    SIGNAL_COLLECTED = "SIGNAL_COLLECTED"
    CATEGORIZED = "CATEGORIZED"
    TRENDING = "TRENDING"
    SKIPPED = "SKIPPED"
    EXPIRED = "EXPIRED"
    RESEARCHED = "RESEARCHED"
    WRITTEN = "WRITTEN"
    GOVERNED = "GOVERNED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class ArticleMode(str, enum.Enum):
    NORMAL = "normal"
    ALLIN = "allin"


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source reference
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("sources.id"))

    # Signal data
    original_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    original_title: Mapped[str] = mapped_column(String(1024), nullable=False)
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_summary: Mapped[Optional[str]] = mapped_column(Text)
    original_image_url: Mapped[Optional[str]] = mapped_column(String(2048))
    signal_published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Analysis
    category: Mapped[Optional[str]] = mapped_column(String(100))
    category_confidence: Mapped[Optional[float]] = mapped_column(Float)
    trend_score: Mapped[Optional[float]] = mapped_column(Float)
    article_type: Mapped[str] = mapped_column(String(20), default="quick")

    # Research
    crawled_content: Mapped[Optional[str]] = mapped_column(Text)
    crawled_images: Mapped[list] = mapped_column(JSONB, default=list)

    # Written content
    body_html: Mapped[Optional[str]] = mapped_column(Text)
    meta_title: Mapped[Optional[str]] = mapped_column(String(255))
    meta_description: Mapped[Optional[str]] = mapped_column(String(500))
    slug: Mapped[Optional[str]] = mapped_column(String(255))
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    image_keywords: Mapped[list] = mapped_column(JSONB, default=list)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)

    # Governance
    governance_result: Mapped[Optional[str]] = mapped_column(String(20))
    governance_reason: Mapped[Optional[str]] = mapped_column(Text)
    copyright_score: Mapped[Optional[float]] = mapped_column(Float)

    # Publishing
    wp_post_id: Mapped[Optional[int]] = mapped_column(Integer)
    wp_url: Mapped[Optional[str]] = mapped_column(String(2048))
    featured_image_wp_id: Mapped[Optional[int]] = mapped_column(Integer)
    image_source_credit: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # SEO tracking
    indexed_google: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    indexed_bing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    internal_links_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    indexing_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # State machine
    state: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ArticleState.SIGNAL_COLLECTED.value, index=True
    )
    mode: Mapped[str] = mapped_column(String(10), nullable=False, default=ArticleMode.NORMAL.value)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fail_reason: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_step_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    source: Mapped[Optional["Source"]] = relationship("Source", back_populates="articles")
    publish_logs: Mapped[list["PublishLog"]] = relationship(
        "PublishLog", back_populates="article", order_by="PublishLog.created_at.desc()"
    )

    __table_args__ = (
        Index("idx_articles_priority", "priority", "queued_at"),
        Index("idx_articles_created", "created_at"),
        UniqueConstraint("original_url", name="uq_articles_url"),
        Index("idx_articles_wp_post", "wp_post_id", postgresql_where=wp_post_id.isnot(None)),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "source_id": str(self.source_id) if self.source_id else None,
            "original_url": self.original_url,
            "original_title": self.original_title,
            "title_hash": self.title_hash,
            "original_summary": self.original_summary,
            "original_image_url": self.original_image_url,
            "signal_published_at": self.signal_published_at.isoformat() if self.signal_published_at else None,
            "category": self.category,
            "category_confidence": self.category_confidence,
            "trend_score": self.trend_score,
            "article_type": self.article_type,
            "crawled_content": self.crawled_content,
            "crawled_images": self.crawled_images,
            "body_html": self.body_html,
            "meta_title": self.meta_title,
            "meta_description": self.meta_description,
            "slug": self.slug,
            "tags": self.tags,
            "image_keywords": self.image_keywords,
            "word_count": self.word_count,
            "governance_result": self.governance_result,
            "governance_reason": self.governance_reason,
            "copyright_score": self.copyright_score,
            "wp_post_id": self.wp_post_id,
            "wp_url": self.wp_url,
            "featured_image_wp_id": self.featured_image_wp_id,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "state": self.state,
            "mode": self.mode,
            "priority": self.priority,
            "fail_reason": self.fail_reason,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

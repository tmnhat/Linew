"""
PublishLog model for audit trail.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base


class PublishLog(Base):
    __tablename__ = "publish_logs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    wp_post_id: Mapped[int] = mapped_column(Integer)
    wp_response: Mapped[dict] = mapped_column(JSONB)
    error: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    article: Mapped["Article"] = relationship("Article", back_populates="publish_logs")

    __table_args__ = (
        Index("idx_publish_logs_article", "article_id", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "article_id": str(self.article_id),
            "action": self.action,
            "wp_post_id": self.wp_post_id,
            "wp_response": self.wp_response,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

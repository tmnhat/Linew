"""
TokenUsage model for AI token tracking and cost calculation.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    request_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    article_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), index=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_token_usage_created", "created_at"),
        Index("idx_token_usage_task_model", "task_type", "model"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "task_type": self.task_type,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost": float(self.estimated_cost) if self.estimated_cost else None,
            "request_id": self.request_id,
            "article_id": str(self.article_id) if self.article_id else None,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

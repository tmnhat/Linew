"""
Distributed Lock Model - Database-based fallback when Redis is unavailable.

This model provides a simple distributed locking mechanism using the database
when Redis is down, ensuring we can still prevent duplicate article processing.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class DistributedLock(Base):
    """
    Database-based distributed lock for fallback when Redis is unavailable.
    
    This provides a last-resort mechanism to prevent race conditions
    during article processing.
    """
    __tablename__ = "distributed_locks"

    id: Mapped[str] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    lock_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "title_hash", "article"
    lock_key: Mapped[str] = mapped_column(String(255), nullable=False)  # The actual hash/ID
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False)  # Worker ID
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Index for quick lookups by lock_type and lock_key
        Index("idx_distributed_locks_type_key", "lock_type", "lock_key"),
        # Index for cleanup queries
        Index("idx_distributed_locks_expires", "expires_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "lock_type": self.lock_type,
            "lock_key": self.lock_key,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

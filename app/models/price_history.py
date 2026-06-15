"""
PriceHistory model for prediction data.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, Date, DateTime, Numeric, BigInteger, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    adjusted_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(String(20), default="yahoo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_price_history_symbol_date"),
        Index("idx_price_history_symbol_date", "symbol", "date"),
        Index("idx_price_history_created", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "date": self.date.isoformat() if self.date else None,
            "open": float(self.open) if self.open else None,
            "high": float(self.high) if self.high else None,
            "low": float(self.low) if self.low else None,
            "close": float(self.close) if self.close else None,
            "adjusted_close": float(self.adjusted_close) if self.adjusted_close else None,
            "volume": self.volume,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

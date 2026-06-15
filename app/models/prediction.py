"""
Prediction model for forecasting results.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Date, DateTime, Numeric, UniqueConstraint, Integer, Float, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    low_bound: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    high_bound: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    model_used: Mapped[str] = mapped_column(String(50))
    horizon_days: Mapped[int] = mapped_column(Integer, default=7)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    actual_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "prediction_date", "model_used", name="uq_predictions_symbol_date_model"),
        Index("idx_predictions_symbol_date", "symbol", "prediction_date"),
        Index("idx_predictions_generated", "generated_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "prediction_date": self.prediction_date.isoformat() if self.prediction_date else None,
            "predicted_price": float(self.predicted_price) if self.predicted_price else None,
            "low_bound": float(self.low_bound) if self.low_bound else None,
            "high_bound": float(self.high_bound) if self.high_bound else None,
            "model_used": self.model_used,
            "horizon_days": self.horizon_days,
            "confidence_score": self.confidence_score,
            "actual_price": float(self.actual_price) if self.actual_price else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }

"""
Prediction System SQLAlchemy models.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import String, Date, DateTime, Numeric, Integer, Float, Text, Index, BigInteger
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    rsi_14: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    macd_line: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    macd_signal: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    macd_histogram: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    bb_upper: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    bb_middle: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    bb_lower: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    sma_20: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    sma_50: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    sma_200: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    ema_12: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    ema_26: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    atr_14: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)
    volume_sma_20: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("uq_technical_indicators_symbol_date", "symbol", "date", unique=True),
        Index("idx_technical_indicators_symbol_date", "symbol", "date"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "date": self.date.isoformat() if self.date else None,
            "rsi_14": float(self.rsi_14) if self.rsi_14 else None,
            "macd_line": float(self.macd_line) if self.macd_line else None,
            "macd_signal": float(self.macd_signal) if self.macd_signal else None,
            "macd_histogram": float(self.macd_histogram) if self.macd_histogram else None,
            "bb_upper": float(self.bb_upper) if self.bb_upper else None,
            "bb_middle": float(self.bb_middle) if self.bb_middle else None,
            "bb_lower": float(self.bb_lower) if self.bb_lower else None,
            "sma_20": float(self.sma_20) if self.sma_20 else None,
            "sma_50": float(self.sma_50) if self.sma_50 else None,
            "sma_200": float(self.sma_200) if self.sma_200 else None,
            "ema_12": float(self.ema_12) if self.ema_12 else None,
            "ema_26": float(self.ema_26) if self.ema_26 else None,
            "atr_14": float(self.atr_14) if self.atr_14 else None,
            "volume": self.volume,
            "volume_sma_20": float(self.volume_sma_20) if self.volume_sma_20 else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MarketResearch(Base):
    __tablename__ = "market_research"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    sentiment: Mapped[Optional[str]] = mapped_column(String(20))
    sentiment_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    analysis_text: Mapped[Optional[str]] = mapped_column(Text)
    analysis_vi: Mapped[Optional[str]] = mapped_column(Text)
    key_factors: Mapped[List[dict]] = mapped_column(JSONB, default=list)
    risk_factors: Mapped[List[dict]] = mapped_column(JSONB, default=list)
    why_moving: Mapped[List[str]] = mapped_column(JSONB, default=list)  # NEW: detailed reasons
    risks: Mapped[List[str]] = mapped_column(JSONB, default=list)  # NEW: specific risks
    opportunities: Mapped[List[str]] = mapped_column(JSONB, default=list)  # NEW: opportunities
    support_levels: Mapped[List[float]] = mapped_column(JSONB, default=list)
    resistance_levels: Mapped[List[float]] = mapped_column(JSONB, default=list)
    fear_greed_index: Mapped[Optional[int]] = mapped_column(Integer)
    fear_greed_value: Mapped[Optional[str]] = mapped_column(String(20))
    model_used: Mapped[str] = mapped_column(String(50), default="minimax-m2.5")
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_market_research_symbol_date", "symbol", "analysis_date"),
        Index("idx_market_research_generated", "generated_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "analysis_date": self.analysis_date.isoformat() if self.analysis_date else None,
            "sentiment": self.sentiment,
            "sentiment_score": float(self.sentiment_score) if self.sentiment_score else None,
            "analysis_text": self.analysis_text,
            "analysis_vi": self.analysis_vi,
            "key_factors": self.key_factors or [],
            "risk_factors": self.risk_factors or [],
            "why_moving": self.why_moving or [],
            "risks": self.risks or [],
            "opportunities": self.opportunities or [],
            "support_levels": self.support_levels or [],
            "resistance_levels": self.resistance_levels or [],
            "fear_greed_index": self.fear_greed_index,
            "fear_greed_value": self.fear_greed_value,
            "model_used": self.model_used,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }


class PredictionFinal(Base):
    __tablename__ = "prediction_final"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    market: Mapped[Optional[str]] = mapped_column(String(10))  # crypto, vn, us
    currency: Mapped[str] = mapped_column(String(5), default="USD")
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    predicted_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    predicted_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    predicted_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    timesfm_prediction: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    chronos_prediction: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    ensemble_weight_timesfm: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    ensemble_weight_chronos: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    ai_sentiment: Mapped[Optional[str]] = mapped_column(String(20))
    ai_sentiment_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    ai_adjustment_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    technical_signals: Mapped[dict] = mapped_column(JSONB, default=dict)
    model_used: Mapped[str] = mapped_column(String(50))
    actual_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    accuracy_error_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("uq_prediction_final_symbol_date_horizon", "symbol", "prediction_date", "horizon_days", unique=True),
        Index("idx_prediction_final_symbol_date", "symbol", "prediction_date"),
        Index("idx_prediction_final_horizon", "horizon_days"),
        Index("idx_prediction_final_generated", "generated_at"),
        Index("idx_prediction_final_market", "market"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "prediction_date": self.prediction_date.isoformat() if self.prediction_date else None,
            "horizon_days": self.horizon_days,
            "current_price": float(self.current_price) if self.current_price else None,
            "predicted_price": float(self.predicted_price) if self.predicted_price else None,
            "predicted_low": float(self.predicted_low) if self.predicted_low else None,
            "predicted_high": float(self.predicted_high) if self.predicted_high else None,
            "change_pct": float(self.change_pct) if self.change_pct else None,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "timesfm_prediction": float(self.timesfm_prediction) if self.timesfm_prediction else None,
            "chronos_prediction": float(self.chronos_prediction) if self.chronos_prediction else None,
            "ensemble_weight_timesfm": float(self.ensemble_weight_timesfm) if self.ensemble_weight_timesfm else None,
            "ensemble_weight_chronos": float(self.ensemble_weight_chronos) if self.ensemble_weight_chronos else None,
            "ai_sentiment": self.ai_sentiment,
            "ai_sentiment_score": float(self.ai_sentiment_score) if self.ai_sentiment_score else None,
            "ai_adjustment_pct": float(self.ai_adjustment_pct) if self.ai_adjustment_pct else None,
            "technical_signals": self.technical_signals or {},
            "model_used": self.model_used,
            "actual_price": float(self.actual_price) if self.actual_price else None,
            "accuracy_error_pct": float(self.accuracy_error_pct) if self.accuracy_error_pct else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }

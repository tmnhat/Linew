"""
Tracked symbols and search cache models.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TrackedSymbol(Base):
    """Symbol being tracked for predictions."""
    __tablename__ = "tracked_symbols"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # crypto, vn, us
    exchange: Mapped[Optional[str]] = mapped_column(String(20))  # HOSE, HNX, NASDAQ, etc
    currency: Mapped[str] = mapped_column(String(5), default="USD")

    # Tracking flags
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    popularity: Mapped[int] = mapped_column(Integer, default=0)

    # Data availability
    has_prediction: Mapped[bool] = mapped_column(Boolean, default=False)
    last_price: Mapped[Optional[float]] = mapped_column(nullable=True)
    last_updated: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index("uq_tracked_symbols_symbol_market", "symbol", "market", unique=True),
        Index("idx_tracked_symbols_market_active", "market", "is_active"),
        Index("idx_tracked_symbols_popularity", "popularity"),
        Index("idx_tracked_symbols_default", "is_default", postgresql_where=is_default == True),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "exchange": self.exchange,
            "currency": self.currency,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "popularity": self.popularity,
            "has_prediction": self.has_prediction,
            "last_price": self.last_price,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SymbolSearchCache(Base):
    """Pre-populated symbol cache for search autocomplete."""
    __tablename__ = "symbol_search_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    exchange: Mapped[Optional[str]] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(5), default="USD")
    search_text: Mapped[Optional[str]] = mapped_column(String(500))

    __table_args__ = (
        Index("uq_symbol_search_cache_symbol_market", "symbol", "market", unique=True),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "exchange": self.exchange,
            "currency": self.currency,
            "search_text": self.search_text,
        }

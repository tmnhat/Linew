"""
Pydantic models for distribution module.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class DistributionResult(BaseModel):
    """Result from a distribution operation."""
    status: str = Field(..., description="Status: success, failed, pending, skipped")
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    error: Optional[str] = None
    channel: str


class DistributionStats(BaseModel):
    """Distribution statistics per channel."""
    channel: str
    total: int = 0
    success: int = 0
    failed: int = 0
    pending: int = 0
    success_rate: float = 0.0


class DistributionStatsResponse(BaseModel):
    """Overall distribution statistics."""
    telegram: DistributionStats
    facebook: DistributionStats
    twitter: DistributionStats
    newsletter: DistributionStats
    today_articles: int = 0
    today_distributed: int = 0


class NewsletterSubscribeRequest(BaseModel):
    """Newsletter subscription request."""
    email: EmailStr
    name: Optional[str] = None
    categories: list[str] = ["tech", "finance"]
    frequency: str = "daily"


class NewsletterSubscribeResponse(BaseModel):
    """Newsletter subscription response."""
    success: bool
    message: str
    subscriber_id: Optional[str] = None


class NewsletterUnsubscribeRequest(BaseModel):
    """Newsletter unsubscription request."""
    email: EmailStr


class NewsletterStatsResponse(BaseModel):
    """Newsletter statistics."""
    total: int = 0
    active: int = 0
    inactive: int = 0
    by_category: dict[str, int] = {}


class SubscriberResponse(BaseModel):
    """Subscriber information (public fields only)."""
    id: str
    email: str
    name: Optional[str]
    is_active: bool
    categories: list[str]
    frequency: str
    subscribed_at: datetime
    total_sent: int = 0
    total_opened: int = 0

    class Config:
        from_attributes = True

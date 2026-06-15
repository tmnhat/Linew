"""
Distribution module - auto-post to social media and newsletter.
"""
from app.distribution.service import DistributionService
from app.distribution.models import (
    DistributionResult,
    NewsletterSubscribeRequest,
    NewsletterSubscribeResponse,
)

__all__ = [
    "DistributionService",
    "DistributionResult",
    "NewsletterSubscribeRequest",
    "NewsletterSubscribeResponse",
]

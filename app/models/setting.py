"""
Setting model for key-value configuration.
"""
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Default settings
DEFAULT_SETTINGS = {
    "scheduler": {
        "rss_interval_minutes": 30,
        "pipeline_interval_minutes": 60,
    },
    "pipeline": {
        "auto_publish": True,
        "trend_scoring_enabled": True,
        "governance_enabled": True,
        "default_mode": "normal",
        "active_categories": ["tech", "finance"],
        "signal_expiry_hours": 24,
        "trending_only_mode": False,
        "min_trend_score": 0.5,
        "topic_cooldown_hours": 2,
        "max_articles_per_topic_per_cooldown": 3,
    },
    "ai": {
        "gateway_url": "https://api.openai.com/v1",
        "api_key": "",
        "writer_model": "gpt-4o",
        "researcher_model": "claude-3-5-sonnet",
        "light_model": "gpt-4o-mini",
        "summarizer_model": "gpt-4o-mini",
    },
    "wordpress": {
        "site_url": "",
        "username": "",
        "app_password": "",
    },
    "prediction": {
        "symbols": [
            {"symbol": "BTC-USD", "name": "Bitcoin", "type": "crypto"},
            {"symbol": "ETH-USD", "name": "Ethereum", "type": "crypto"},
            {"symbol": "^VNINDEX", "name": "VN-Index", "type": "stock"},
        ],
        "horizon_days": 7,
        "update_frequency": "daily",
    },
    "cleanup": {
        "expired_days": 30,
        "skipped_days": 7,
        "price_history_years": 2,
        "predictions_days": 90,
        "publish_logs_days": 90,
    },
    "distribution": {
        "telegram_channel_enabled": True,
        "telegram_channel_id": "@linews_vn",
        "facebook_enabled": True,
        "facebook_paused": False,
        "facebook_schedule_minutes": 80,
        "facebook_min_trend_score": 0.3,
        "facebook_auto_post": False,
        "twitter_enabled": True,
        "twitter_paused": False,
        "newsletter_enabled": True,
        "medium_enabled": False,
        "viblo_enabled": False,
    },
    "newsletter": {
        "frequency": "daily",
        "send_time": "07:00",
    },
    "storage": {
        "raw_signals_retention_days": 60,
        "articles_retention_days": 30,
        "predictions_retention_days": 90,
        "price_history_retention_days": 730,
        "publish_logs_retention_days": 90,
        "archive_base_dir": "/data/archive",
        "backup_base_dir": "/data/backup",
    },
    "backup": {
        "last_run": None,
        "last_run_success": None,
        "gdrive_remote": "gdrive",
        "gdrive_base_dir": "Linew-Backups",
        "local_retention_days": 7,
        "drive_retention_days": 90,
    },
}

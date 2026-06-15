"""
Pydantic Settings - all environment variables.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://linew:changeme@postgres:5432/linew"
    db_password: str = "changeme"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # AI Gateway - OpenAI compatible API
    ai_gateway_url: str = "https://api.openai.com/v1"
    ai_gateway_key: str = ""

    # Vertex AI - MiniMax via Vertex
    vertex_api_key: str = ""
    vertex_project_id: str = "minimax-chat"
    vertex_location: str = "global"
    vertex_base_url: str = "https://vertex-key.com/api/v1"

    # AI Models
    ai_writer_model: str = "gpt-4o"
    ai_light_model: str = "gpt-4o-mini"
    ai_researcher_model: str = "claude-3-5-sonnet"
    ai_summarizer_model: str = "gpt-4o-mini"

    # WordPress
    wp_url: str = "https://example.com"
    wp_username: str = "admin"
    wp_app_password: str = "xxxx-xxxx-xxxx-xxxx"

    # Unsplash API
    unsplash_access_key: str = ""

    # FlareSolverr
    flaresolverr_url: str = "http://flaresolverr:8191/v1"

    # Application
    secret_key: str = "change-this-secret-key"
    environment: str = "development"
    log_level: str = "info"

    # Dashboard Authentication
    dashboard_username: str = "admin"
    dashboard_password: str = "changeme"

    # TimesFM
    timesfm_device: str = "mps"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Distribution - Telegram
    telegram_bot_token: str = ""
    telegram_channel_id: str = "@linews_vn"
    telegram_channel_enabled: bool = True

    # Distribution - Facebook
    facebook_page_id: str = ""
    facebook_page_access_token: str = ""
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_enabled: bool = True
    facebook_schedule_minutes: int = 80
    facebook_min_trend_score: float = 0.3
    facebook_article_search_hours: int = 24  # Search window for finding articles

    # Distribution - Twitter/X
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_secret: str = ""
    twitter_enabled: bool = True

    # Newsletter
    newsletter_enabled: bool = True
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    newsletter_from_name: str = "Linews"
    newsletter_from_email: str = "linews@gmail.com"

    # Analytics & SEO
    ga_measurement_id: str = ""
    site_url: str = "https://example.com"
    site_name: str = "Linews"

    # Google Indexing API (for SEO ping)
    google_service_account_json: str = ""
    google_site_url: str = "https://example.com/"

    # Bing Webmaster API (for SEO ping)
    bing_api_key: str = ""

    # Internal Linking
    internal_linking_enabled: bool = True
    internal_links_per_article: int = 3
    max_articles_to_update: int = 50

    # CORS - comma-separated list of allowed origins
    cors_origins: str = ""  # Empty = allow all for dev, set specific origins for production

    # API Security
    api_key: str = ""  # Set in .env - empty = no auth (dev only)

    # Facebook API
    facebook_api_version: str = "v21.0"  # Graph API version

    # Prediction V2 - API Keys
    fred_api_key: str = ""  # FRED API key - https://fred.stlouisfed.org/docs/api/api_key.html
    finnhub_api_key: str = ""  # Finnhub API key - https://finnhub.io
    fincept_api_key: str = ""  # Fincept API key (optional)
    lunarcrush_api_key: str = ""  # Lunarcrush API key - https://lunarcrush.com/developers

    # Prediction V2 - Feature Flags
    prediction_enable_fundamental: bool = True  # L2 Layer: P/E, EPS, Revenue
    prediction_enable_macro: bool = True  # L3 Layer: Fed rate, CPI, GDP
    prediction_enable_onchain: bool = True  # L4 Layer: DeFi metrics
    prediction_enable_events: bool = True  # L5 Layer: FOMC, Earnings

    # Prediction V3 - Feature Flags
    prediction_enable_multi_agent: bool = True  # Multi-agent AI (TrendAgent, ValueAgent, etc.)
    prediction_enable_adaptive_weights: bool = True  # Phase A1: Adaptive agent weights
    prediction_enable_regime_detection: bool = True  # Phase A2: Market regime detection
    prediction_enable_mtf: bool = True  # Phase A3: Multi-timeframe analysis (crypto + US)
    prediction_enable_options: bool = True  # Phase B1: Options signals (US + BTC/ETH)
    prediction_enable_social: bool = True  # Phase B2: Social sentiment
    prediction_enable_correlation: bool = True  # Phase B3: Cross-asset correlation

    # Prediction V3 - Calibration & Backtest
    prediction_calibration_enabled: bool = True  # Platt scaling calibration
    prediction_backtest_min_accuracy: float = 0.55  # Alert neu accuracy < 55%

    # Prediction V2 - Data Layer Cache TTL (seconds)
    cache_ttl_fundamental: int = 86400  # 24 hours
    cache_ttl_macro: int = 21600  # 6 hours
    cache_ttl_onchain: int = 3600  # 1 hour
    cache_ttl_events: int = 43200  # 12 hours

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

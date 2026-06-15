"""
FastAPI main application.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import get_settings
from app.core.database import init_db, close_db
from app.core.redis import close_redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _validate_security_settings(settings):
    """Warn loudly about insecure default settings."""
    warnings = []

    if settings.secret_key in ("change-this-secret-key", "changeme", "secret", ""):
        warnings.append("SECRET_KEY is using an insecure default value!")

    if settings.db_password in ("changeme", "password", ""):
        warnings.append("DB_PASSWORD is using an insecure default value!")

    if settings.environment == "production":
        if not settings.api_key:
            warnings.append("API_KEY is empty - all endpoints are unauthenticated in production!")
        if not settings.cors_origins:
            warnings.append("CORS_ORIGINS is empty - allowing ALL origins in production!")
        for w in warnings:
            logger.critical(f"Security warning: {w}")
        # In production, fail fast on critical issues
        if settings.secret_key in ("change-this-secret-key", "changeme", ""):
            raise RuntimeError("FATAL: Cannot start in production with default SECRET_KEY!")
    else:
        for w in warnings:
            logger.warning(f"Security warning (dev mode): {w}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Linew API...")
    settings = get_settings()
    logger.info(f"Environment: {settings.environment}")

    # Validate security settings
    await _validate_security_settings(settings)

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Linew API...")
    await close_db()
    await close_redis()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Linew API",
    description="AI Media Platform - Automated news collection, analysis, and publishing",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS configuration
settings = get_settings()
if settings.cors_origins:
    cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    logger.info(f"CORS: {len(cors_origins)} allowed origin(s)")
else:
    cors_origins = ["*"]
    if settings.is_production:
        logger.warning(
            "CORS_ORIGINS is empty in production - allowing ALL origins. "
            "Set CORS_ORIGINS in .env to restrict access."
        )
    else:
        logger.debug("CORS: allowing all origins (development mode)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
from app.signals.router import router as signals_router
from app.pipeline.router import router as pipeline_router
from app.publisher.router import router as publisher_router
from app.prediction.router import router as prediction_router
from app.routers.articles import router as articles_router
from app.routers.stats import router as stats_router
from app.routers.settings import router as settings_router
from app.routers.health import router as health_router
from app.routers.ws import router as ws_router
from app.widget.router import router as widget_router
from app.seo.router import router as seo_router
from app.distribution.router import router as distribution_router
from app.routers.storage import router as storage_router
from app.feed.router import router as feed_router
from app.routers.dashboard_auth import router as dashboard_auth_router

app.include_router(signals_router)
app.include_router(pipeline_router)
app.include_router(publisher_router)
app.include_router(prediction_router)
app.include_router(articles_router)
app.include_router(stats_router)
app.include_router(settings_router)
app.include_router(health_router)
app.include_router(ws_router)
app.include_router(widget_router)
app.include_router(seo_router)
app.include_router(distribution_router)
app.include_router(storage_router)
app.include_router(feed_router)
app.include_router(dashboard_auth_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Linew API",
        "version": "1.0.0",
        "status": "running",
    }

"""
Settings API routes.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.setting import Setting, DEFAULT_SETTINGS
from app.core.ai_gateway import test_ai_connection, circuit_breaker
from app.core.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    scheduler: dict
    pipeline: dict
    ai: dict
    wordpress: dict
    prediction: dict
    distribution: dict
    newsletter: dict
    seo: dict
    social: dict
    smtp: dict


class SettingUpdate(BaseModel):
    scheduler: dict | None = None
    pipeline: dict | None = None
    ai: dict | None = None
    wordpress: dict | None = None
    prediction: dict | None = None
    distribution: dict | None = None
    newsletter: dict | None = None
    seo: dict | None = None
    social: dict | None = None
    smtp: dict | None = None


# Default values for new settings
DEFAULT_SEO = {
    "ga_measurement_id": "",
    "site_url": "https://litimez.ai",
    "site_name": "Linews",
}

DEFAULT_SOCIAL = {
    "telegram_bot_token": "",
    "facebook_page_id": "",
    "facebook_page_access_token": "",
    "twitter_api_key": "",
    "twitter_api_secret": "",
    "twitter_access_token": "",
    "twitter_access_secret": "",
}

DEFAULT_SMTP = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_password": "",
    "newsletter_from_name": "Linews",
    "newsletter_from_email": "linews@gmail.com",
}


class AITestRequest(BaseModel):
    gateway_url: str
    api_key: str
    model: str = "gpt-4o-mini"


class AITestResponse(BaseModel):
    success: bool
    message: str
    status_code: int | None = None


def _merge_with_defaults(stored: dict | None, defaults: dict) -> dict:
    """Merge stored settings with defaults, filling in missing keys."""
    if not stored:
        return defaults
    return {**defaults, **stored}


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get all settings with complete defaults applied."""
    result = await db.execute(select(Setting))
    settings = result.scalars().all()

    # Build response from database settings
    response = {}
    for s in settings:
        response[s.key] = s.value

    return SettingsResponse(
        scheduler=_merge_with_defaults(response.get("scheduler"), DEFAULT_SETTINGS["scheduler"]),
        pipeline=_merge_with_defaults(response.get("pipeline"), DEFAULT_SETTINGS["pipeline"]),
        ai=_merge_with_defaults(response.get("ai"), DEFAULT_SETTINGS["ai"]),
        wordpress=_merge_with_defaults(response.get("wordpress"), DEFAULT_SETTINGS["wordpress"]),
        prediction=_merge_with_defaults(response.get("prediction"), DEFAULT_SETTINGS["prediction"]),
        distribution=_merge_with_defaults(response.get("distribution"), DEFAULT_SETTINGS.get("distribution", {})),
        newsletter=_merge_with_defaults(response.get("newsletter"), DEFAULT_SETTINGS.get("newsletter", {})),
        seo=_merge_with_defaults(response.get("seo"), DEFAULT_SEO),
        social=_merge_with_defaults(response.get("social"), DEFAULT_SOCIAL),
        smtp=_merge_with_defaults(response.get("smtp"), DEFAULT_SMTP),
    )


@router.put("")
async def update_settings(
    data: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_auth),
):
    """Update settings."""
    updated_keys = []

    for key, value in data.model_dump(exclude_unset=True).items():
        # Get existing setting
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()

        if setting:
            # Update existing
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            # Create new
            setting = Setting(key=key, value=value)
            db.add(setting)

        updated_keys.append(key)

    await db.commit()
    logger.info(f"Settings updated: {updated_keys}")

    # Invalidate schedule cache when scheduler or distribution settings change
    scheduler_keys = {"scheduler", "distribution", "newsletter"}
    if any(k in scheduler_keys for k in updated_keys):
        try:
            import redis
            from app.config import get_settings
            from app.worker.scheduler import SCHEDULE_SETTINGS_KEY

            settings = get_settings()
            r = redis.from_url(settings.redis_url, decode_responses=True)
            r.delete(SCHEDULE_SETTINGS_KEY)
            logger.info("Schedule cache invalidated")
        except Exception as e:
            logger.warning(f"Failed to invalidate schedule cache: {e}")

    return {"updated_keys": updated_keys}


@router.post("/test-ai", response_model=AITestResponse)
async def test_ai(
    data: AITestRequest,
):
    """Test AI connection with given settings."""
    logger.info(f"Testing AI connection to {data.gateway_url} with model {data.model}")
    result = await test_ai_connection(
        gateway_url=data.gateway_url,
        api_key=data.api_key,
        model=data.model,
    )
    return AITestResponse(**result)


@router.post("/reset-circuit-breaker")
async def reset_circuit_breaker():
    """Reset AI circuit breaker."""
    circuit_breaker.reset()
    return {"message": "Circuit breaker reset successfully"}


@router.post("/reload-schedule")
async def reload_schedule_cache():
    """
    Force reload the schedule cache from database.
    Call this after updating scheduler settings if Celery Beat is running
    with static schedule (requires restart for changes to take effect).
    """
    try:
        from app.worker.scheduler import load_schedule_settings_async
        settings = await load_schedule_settings_async()
        return {
            "message": "Schedule cache reloaded successfully",
            "settings_keys": list(settings.keys()),
        }
    except Exception as e:
        logger.error(f"Failed to reload schedule cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{key}")
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single setting."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        if key in DEFAULT_SETTINGS:
            return {"key": key, "value": DEFAULT_SETTINGS[key]}
        raise HTTPException(status_code=404, detail="Setting not found")

    return {"key": key, "value": setting.value}


@router.put("/{key}")
async def update_setting(
    key: str,
    value: dict,
    db: AsyncSession = Depends(get_db),
):
    """Update a single setting."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = value
        setting.updated_at = datetime.utcnow()
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)

    await db.commit()
    logger.info(f"Setting updated: {key}")

    return {"key": key, "value": value}

"""
Dashboard Authentication Router
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Simple token storage (in production, use Redis)
_tokens: dict[str, dict] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    expires_in: int = 3600


def _generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def _validate_credentials(username: str, password: str) -> bool:
    """Validate the provided username and password."""
    settings = get_settings()
    return username == settings.dashboard_username and password == settings.dashboard_password


def _cleanup_expired_tokens():
    """Remove expired tokens from storage."""
    now = datetime.utcnow()
    expired = [token for token, data in _tokens.items() if data["expires_at"] < now]
    for token in expired:
        del _tokens[token]


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, response: Response):
    """
    Authenticate with dashboard username and password.
    Returns a session token valid for 24 hours.
    """
    _cleanup_expired_tokens()

    body = await request.json()
    username = body.get("username")
    password = body.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    if not _validate_credentials(username, password):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")

    # Generate new token
    token = _generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=24)

    _tokens[token] = {
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
    }

    # Determine if secure (HTTPS) based on forwarded header
    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    is_secure = forwarded_proto == "https"

    # Set HTTP-only cookie
    response.set_cookie(
        key="dashboard_token",
        value=token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=86400,  # 24 hours
        path="/",
    )

    return LoginResponse(
        success=True,
        message="Đăng nhập thành công",
        expires_in=86400,
    )


@router.post("/logout")
async def logout(response: Response):
    """Logout and clear the session token."""
    response.delete_cookie(key="dashboard_token", path="/")
    return {"success": True, "message": "Đăng xuất thành công"}


@router.get("/verify")
async def verify_token(token: Optional[str] = None, dashboard_token: Optional[str] = Cookie(None)) -> dict:
    """
    Verify if the current session is valid.
    Checks from cookie first, then query parameter as fallback.
    """
    _cleanup_expired_tokens()

    # Check token from cookie (primary method)
    if dashboard_token and dashboard_token in _tokens:
        return {"valid": True}

    # Check token from query param (for API calls)
    if token and token in _tokens:
        return {"valid": True}

    return {"valid": False}


@router.get("/status")
async def auth_status() -> dict:
    """
    Check if authentication is configured.
    Returns whether a dashboard password is set.
    """
    settings = get_settings()
    has_password = bool(settings.dashboard_password and settings.dashboard_password != "changeme")

    return {
        "configured": has_password,
        "message": "Dashboard password is set" if has_password else "No dashboard password configured",
    }

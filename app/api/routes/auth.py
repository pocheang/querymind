"""Authentication routes for the Multi-Agent Local RAG API."""
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from authlib.integrations.starlette_client import OAuth

from app.api.dependencies import (
    _audit,
    _client_ip,
    _clear_auth_cookie,
    _require_user,
    _require_user_and_token,
    _set_auth_cookie,
    auth_service,
    login_limiter,
    register_limiter,
    settings,
)
from app.core.schemas import AuthCredentials, AuthLoginResponse, AuthUser
from app.services.auth.validation import validate_password

router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth setup
oauth = OAuth()
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# Store OAuth state temporarily (in production, use Redis)
_oauth_states: dict[str, dict[str, Any]] = {}


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    display_name: str


@router.post("/register", response_model=AuthUser)
def register(req: AuthCredentials, request: Request):
    ip = _client_ip(request)
    register_key = f"register::{ip}"
    if register_limiter.is_limited(register_key):
        _audit(request, action="auth.register", resource_type="auth", result="blocked", detail="register_rate_limited")
        raise HTTPException(status_code=429, detail="too many register attempts, retry later")
    try:
        validate_password(req.password)
        user = auth_service.register(req.username, req.password)
    except ValueError as e:
        register_limiter.record(register_key)
        _audit(request, action="auth.register", resource_type="auth", result="failed", detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    register_limiter.reset(register_key)
    _audit(request, action="auth.register", resource_type="auth", result="success", resource_id=user["user_id"])
    return AuthUser(**user)


@router.post("/login", response_model=AuthLoginResponse)
def login(req: AuthCredentials, request: Request, response: Response):
    ip = _client_ip(request)
    username_key = (req.username or "").strip().lower() or "unknown"
    login_key = f"login::{ip}::{username_key}"
    if login_limiter.is_limited(login_key):
        _audit(request, action="auth.login", resource_type="auth", result="blocked", detail="login_rate_limited")
        raise HTTPException(status_code=429, detail="too many login attempts, retry later")
    try:
        payload = auth_service.login(req.username, req.password)
    except ValueError as e:
        login_limiter.record(login_key)
        _audit(request, action="auth.login", resource_type="auth", result="failed", detail=str(e))
        raise HTTPException(status_code=401, detail="invalid credentials")
    login_limiter.reset(login_key)
    _audit(
        request,
        action="auth.login",
        resource_type="auth",
        result="success",
        resource_id=payload["user"]["user_id"],
        detail=f"user={payload['user']['username']}",
    )
    token_value = str(payload.get("token", "") or "")
    _set_auth_cookie(response, token_value)
    if not bool(getattr(settings, "auth_expose_token_in_response", False)):
        payload = {**payload, "token": ""}
    return AuthLoginResponse(**payload)


@router.post("/logout")
def logout(request: Request, response: Response, auth: tuple[dict[str, Any], str] = Depends(_require_user_and_token)):
    _user, token = auth
    auth_service.logout(token)
    _clear_auth_cookie(response)
    _audit(request, action="auth.logout", resource_type="auth", result="success", user=_user, resource_id=_user["user_id"])
    return {"ok": True}


@router.get("/me", response_model=AuthUser)
def auth_me(user: dict[str, Any] = Depends(_require_user)):
    return AuthUser(**user)


@router.put("/profile", response_model=AuthUser)
def update_profile(
    req: UpdateProfileRequest,
    request: Request,
    user: dict[str, Any] = Depends(_require_user),
):
    """Update user profile (display name)."""
    user_id = user["user_id"]

    updated_user = auth_service.user_manager.update_user_display_name(
        user_id, req.display_name
    )

    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    _audit(
        request,
        "profile_updated",
        user_id=user_id,
        details={"display_name": req.display_name},
    )

    return AuthUser(**updated_user)


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    user: dict[str, Any] = Depends(_require_user),
):
    """Change user password (requires old password verification)."""
    user_id = user["user_id"]
    username = user["username"]

    # Verify old password
    try:
        auth_service.login(username, req.old_password)
    except ValueError:
        _audit(
            request,
            action="auth.change_password",
            resource_type="auth",
            result="failed",
            user=user,
            resource_id=user_id,
            detail="old_password_incorrect",
        )
        raise HTTPException(status_code=400, detail="旧密码不正确")

    # Validate new password
    try:
        validate_password(req.new_password)
    except ValueError as e:
        _audit(
            request,
            action="auth.change_password",
            resource_type="auth",
            result="failed",
            user=user,
            resource_id=user_id,
            detail=f"validation_failed: {e}",
        )
        raise HTTPException(status_code=400, detail=str(e))

    # Check new password is different from old
    if req.old_password == req.new_password:
        _audit(
            request,
            action="auth.change_password",
            resource_type="auth",
            result="failed",
            user=user,
            resource_id=user_id,
            detail="new_password_same_as_old",
        )
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")

    # Update password
    try:
        auth_service.user_manager.update_password(user_id, req.new_password)
    except Exception as e:
        _audit(
            request,
            action="auth.change_password",
            resource_type="auth",
            result="failed",
            user=user,
            resource_id=user_id,
            detail=f"update_failed: {e}",
        )
        raise HTTPException(status_code=500, detail="密码更新失败")

    _audit(
        request,
        action="auth.change_password",
        resource_type="auth",
        result="success",
        user=user,
        resource_id=user_id,
    )

    return {"ok": True, "message": "密码已成功更改"}


@router.get("/google/login")
async def google_login(request: Request) -> RedirectResponse:
    """Initiate Google OAuth login flow."""
    if not oauth.google:
        raise HTTPException(status_code=501, detail="Google OAuth 未配置")

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {"ip": _client_ip(request)}

    redirect_uri = settings.google_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri, state=state)


@router.get("/google/callback")
async def google_callback(request: Request, response: Response) -> RedirectResponse:
    """Handle Google OAuth callback."""
    if not oauth.google:
        raise HTTPException(status_code=501, detail="Google OAuth 未配置")

    # Verify state
    state = request.query_params.get("state")
    if not state or state not in _oauth_states:
        _audit(
            request,
            action="auth.google_callback",
            resource_type="auth",
            result="blocked",
            detail="invalid_state",
        )
        return RedirectResponse(url="/login?error=invalid_state")

    # Verify IP matches (basic CSRF protection)
    stored_ip = _oauth_states[state].get("ip")
    current_ip = _client_ip(request)
    if stored_ip != current_ip:
        _audit(
            request,
            action="auth.google_callback",
            resource_type="auth",
            result="blocked",
            detail=f"ip_mismatch: {stored_ip} != {current_ip}",
        )
        del _oauth_states[state]
        return RedirectResponse(url="/login?error=security_check_failed")

    # Clean up state
    del _oauth_states[state]

    try:
        # Exchange code for token
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info or not user_info.get("email"):
            _audit(
                request,
                action="auth.google_callback",
                resource_type="auth",
                result="failed",
                detail="no_email_in_response",
            )
            return RedirectResponse(url="/login?error=no_email")

        email = user_info["email"]
        name = user_info.get("name", email.split("@")[0])

        # Check if user exists
        existing_user = auth_service.user_manager.get_user_by_username(email)

        if existing_user:
            # User exists, log them in
            user_id = existing_user["user_id"]
            _audit(
                request,
                action="auth.google_login",
                resource_type="auth",
                result="success",
                user=existing_user,
                resource_id=user_id,
                detail="existing_user",
            )
        else:
            # Create new user
            try:
                # Generate a random password (user won't use it, OAuth only)
                random_password = secrets.token_urlsafe(32)
                user_id = auth_service.user_manager.create_user(
                    username=email,
                    password=random_password,
                    display_name=name,
                )
                existing_user = auth_service.user_manager.get_user(user_id)
                _audit(
                    request,
                    action="auth.google_register",
                    resource_type="auth",
                    result="success",
                    user=existing_user,
                    resource_id=user_id,
                    detail="new_user_created",
                )
            except Exception as e:
                _audit(
                    request,
                    action="auth.google_register",
                    resource_type="auth",
                    result="failed",
                    detail=f"user_creation_failed: {e}",
                )
                return RedirectResponse(url="/login?error=registration_failed")

        # Generate session token
        session_token = auth_service.token_manager.create_token(user_id)
        _set_auth_cookie(response, session_token)

        return RedirectResponse(url="/app")

    except Exception as e:
        _audit(
            request,
            action="auth.google_callback",
            resource_type="auth",
            result="failed",
            detail=f"oauth_error: {e}",
        )
        return RedirectResponse(url="/login?error=oauth_failed")




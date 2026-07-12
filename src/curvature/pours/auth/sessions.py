"""Sessions, CSRF posture, expiry, and shared abuse limits."""

from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from satellites.auth.security import hash_token, new_session_token
from satellites.auth.store import AuthStore, SessionRecord, UserRecord
from starlette.responses import Response

SESSION_COOKIE = "curvature_session"
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class AuthConfig:
    """Security configuration is assembly, never a source edit at deploy time."""

    allowed_origins: frozenset[str]
    secure_cookies: bool = True
    session_seconds: int = 60 * 60 * 24 * 14
    token_seconds: int = 60 * 60 * 24 * 30

    @classmethod
    def testing(cls) -> AuthConfig:
        return cls(allowed_origins=frozenset({"http://testserver"}), secure_cookies=False)


def auth_config(request: Request) -> AuthConfig:
    config = getattr(request.app.state, "auth_config", None)
    if not isinstance(config, AuthConfig):
        raise RuntimeError(
            "Auth requires app.state.auth_config = AuthConfig(allowed_origins=..., "
            "secure_cookies=True)"
        )
    return config


def _origin(value: str) -> str | None:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".casefold()


def require_write_origin(request: Request) -> None:
    """Browser writes must prove which configured origin authored them."""
    if request.method not in WRITE_METHODS:
        return
    source = request.headers.get("origin") or request.headers.get("referer")
    actual = _origin(source) if source else None
    allowed = {origin.casefold().rstrip("/") for origin in auth_config(request).allowed_origins}
    if actual not in allowed:
        raise HTTPException(403, "write origin refused (C-203)")


def start_session(
    request: Request, response: Response, store: AuthStore, user: UserRecord
) -> None:
    config = auth_config(request)
    token = new_session_token()
    store.save_session(SessionRecord(
        token_hash=hash_token(token),
        user_id=user.id,
        expires_at=time.time() + config.session_seconds,
    ))
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=config.session_seconds,
        httponly=True,
        samesite="lax",
        secure=config.secure_cookies,
        path="/",
    )


def end_session(request: Request, response: Response, store: AuthStore) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        store.delete_session(hash_token(token))
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        samesite="lax",
        secure=auth_config(request).secure_cookies,
        path="/",
    )


def rate_limit(
    request: Request, bucket: str, subject: str, *, limit: int, window_seconds: int
) -> None:
    key = hash_token(f"{bucket}:{subject.casefold()}")
    allowed = request.app.state.auth_store.hit_rate_limit(
        key, limit=limit, window_seconds=window_seconds, now=time.time()
    )
    if not allowed:
        raise HTTPException(429, "too many attempts; try again later")


def bearer_user(request: Request) -> UserRecord | None:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    store: AuthStore = request.app.state.auth_store
    record = store.get_token(hash_token(header[7:].strip()))
    if record is None:
        return None
    if record.expires_at < time.time():
        store.delete_token(record.token_hash, record.user_id)
        return None
    return store.get_user_by_id(record.user_id)


def session_user(request: Request) -> UserRecord | None:
    agent = bearer_user(request)
    if agent is not None:
        return agent
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        return None
    store: AuthStore = request.app.state.auth_store
    token_hash = hash_token(token)
    record = store.get_session(token_hash)
    if record is None:
        return None
    if record.expires_at < time.time():
        store.delete_session(token_hash)
        return None
    if request.method in WRITE_METHODS:
        require_write_origin(request)
    return store.get_user_by_id(record.user_id)


def current_user(request: Request) -> UserRecord:
    user = session_user(request)
    if user is None:
        raise HTTPException(303, headers={"Location": "/auth/login"})
    return user


CurrentUser = Annotated[UserRecord, Depends(current_user)]

"""Sessions and the C-203 posture, enforced exactly where sessions
enter the world.

The cookie is SameSite=Lax and HttpOnly. The current_user dependency
carries the Origin check on writes: cookies plus cross-site POST is the
CSRF setup, and the defense lives in the one dependency every
authenticated route already declares. Agents holding bearer tokens
never carry cookies, so they never trip it — borrowed authority stays
clean."""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from satellites.auth.security import hash_token, new_session_token
from satellites.auth.store import AuthStore, SessionRecord, UserRecord
from starlette.responses import Response

SESSION_COOKIE = "curvature_session"
SESSION_SECONDS = 60 * 60 * 24 * 14
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def start_session(response: Response, store: AuthStore, user: UserRecord) -> None:
    token = new_session_token()
    store.save_session(SessionRecord(
        token_hash=hash_token(token),
        user_id=user.id,
        expires_at=time.time() + SESSION_SECONDS,
    ))
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=SESSION_SECONDS, httponly=True, samesite="lax",
        secure=False,  # flip on under TLS; the deploy doc owns this line
    )


def end_session(request: Request, response: Response, store: AuthStore) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        store.delete_session(hash_token(token))
    response.delete_cookie(SESSION_COOKIE)


def _origin_is_local(request: Request) -> bool:
    origin = request.headers.get("origin")
    if origin is None:
        return True  # non-browser clients; cookies don't ride cross-site here
    host = request.headers.get("host", "")
    return origin.removeprefix("https://").removeprefix("http://") == host


def session_user(request: Request) -> UserRecord | None:
    """Resolve the cookie to a user, enforcing C-203 on writes."""
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        return None
    store: AuthStore = request.app.state.auth_store
    record = store.get_session(hash_token(token))
    if record is None or record.expires_at < time.time():
        return None
    if request.method in WRITE_METHODS and not _origin_is_local(request):
        raise HTTPException(403, "cross-origin write refused (C-203)")
    return store.get_user_by_id(record.user_id)


def current_user(request: Request) -> UserRecord:
    user = session_user(request)
    if user is None:
        raise HTTPException(303, headers={"Location": "/auth/login"})
    return user


CurrentUser = Annotated[UserRecord, Depends(current_user)]

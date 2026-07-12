"""OIDC's orbit segment: two redirects and a verified claim. The state
nonce rides the same stash as pending logins; a returning user with
TOTP still owes the second factor — federation does not skip the house
rules."""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Request
from satellites.auth.oidc import authorization_url, exchange_code, verify_id_token
from satellites.auth.routes_totp import stash_pending
from satellites.auth.security import hash_password, new_session_token
from satellites.auth.sessions import start_session
from satellites.auth.store import UserRecord

from curvature import redirect

router = APIRouter()

STATE_SECONDS = 600


def _providers(request: Request) -> dict:
    return getattr(request.app.state, "auth_oidc", {})


def _states(request: Request) -> dict[str, float]:
    stash = getattr(request.app.state, "auth_oidc_states", None)
    if stash is None:
        stash = {}
        request.app.state.auth_oidc_states = stash
    return stash


def _verifier(request: Request):
    """The seam: tests inject a fake; production verifies for real."""
    return getattr(request.app.state, "auth_oidc_verify", verify_id_token)


def _fetch(request: Request):
    from satellites.auth.oidc import _fetch_json

    return getattr(request.app.state, "auth_oidc_fetch", _fetch_json)


@router.get("/oidc/{provider_name}/login")
async def oidc_login(request: Request, provider_name: str):
    provider = _providers(request).get(provider_name)
    if provider is None:
        return redirect("/auth/login?error=credentials")
    state = new_session_token()[:24]
    _states(request)[state] = time.time() + STATE_SECONDS
    return redirect(authorization_url(provider, state, _fetch(request)))


@router.get("/oidc/{provider_name}/callback")
async def oidc_callback(
    request: Request, provider_name: str, code: str = "", state: str = ""
):
    provider = _providers(request).get(provider_name)
    expires = _states(request).pop(state, 0)
    if provider is None or not code or expires < time.time():
        return redirect("/auth/login?error=credentials")
    id_token = exchange_code(provider, code, _fetch(request))
    claims = _verifier(request)(provider, id_token, _fetch(request))
    email = str(claims.get("email", "")).lower()
    if not email:
        return redirect("/auth/login?error=credentials")
    store = request.app.state.auth_store
    user = store.get_user_by_email(email)
    if user is None:
        user = UserRecord(
            id=uuid.uuid4().hex,
            email=email,
            # No usable password: this identity signs in at its issuer.
            password_hash=hash_password(new_session_token()),
        )
        store.save_user(user)
    if user.totp_secret:
        nonce = stash_pending(request, user.id)
        return redirect(f"/auth/totp/check?pending={nonce}")
    response = redirect("/")
    start_session(response, store, user)
    return response

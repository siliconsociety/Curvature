"""Browser-bound OIDC Authorization Code flow with PKCE and nonce."""

from __future__ import annotations

import hmac
import json
import time
import uuid

from fastapi import APIRouter, Request
from satellites.auth.oidc import (
    authorization_url,
    exchange_code,
    pkce_pair,
    verify_id_token,
)
from satellites.auth.routes_totp import stash_pending
from satellites.auth.security import hash_token, new_session_token
from satellites.auth.sessions import auth_config, rate_limit, start_session
from satellites.auth.store import ChallengeRecord, DuplicateUserError, UserRecord

from curvature import redirect

router = APIRouter()
STATE_SECONDS = 600
OIDC_COOKIE = "curvature_oidc"


def _providers(request: Request) -> dict:
    return getattr(request.app.state, "auth_oidc", {})


def _verifier(request: Request):
    return getattr(request.app.state, "auth_oidc_verify", verify_id_token)


def _fetch(request: Request):
    from satellites.auth.oidc import _fetch_json

    return getattr(request.app.state, "auth_oidc_fetch", _fetch_json)


def _failure(request: Request):
    response = redirect("/auth/login?error=credentials")
    response.delete_cookie(
        OIDC_COOKIE,
        httponly=True,
        samesite="lax",
        secure=auth_config(request).secure_cookies,
        path="/auth/oidc",
    )
    return response


@router.get("/oidc/{provider_name}/login")
def oidc_login(request: Request, provider_name: str):
    provider = _providers(request).get(provider_name)
    if provider is None:
        return _failure(request)
    client = request.client.host if request.client else "unknown"
    rate_limit(request, "oidc-start", f"{client}:{provider_name}", limit=20, window_seconds=600)
    state = new_session_token()
    nonce = new_session_token()
    binder = new_session_token()
    verifier, challenge = pkce_pair()
    request.app.state.auth_store.save_challenge(ChallengeRecord(
        token_hash=hash_token(state),
        kind="oidc",
        payload=json.dumps({
            "provider": provider_name,
            "nonce": nonce,
            "verifier": verifier,
            "binder_hash": hash_token(binder),
        }),
        expires_at=time.time() + STATE_SECONDS,
    ))
    response = redirect(authorization_url(
        provider, state, nonce, challenge, _fetch(request)
    ))
    config = auth_config(request)
    response.set_cookie(
        OIDC_COOKIE,
        binder,
        max_age=STATE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=config.secure_cookies,
        path="/auth/oidc",
    )
    return response


@router.get("/oidc/{provider_name}/callback")
def oidc_callback(
    request: Request, provider_name: str, code: str = "", state: str = ""
):
    provider = _providers(request).get(provider_name)
    challenge = request.app.state.auth_store.pop_challenge(
        hash_token(state), "oidc", time.time()
    )
    if provider is None or not code or challenge is None:
        return _failure(request)
    transaction = json.loads(challenge.payload)
    binder = request.cookies.get(OIDC_COOKIE, "")
    if transaction.get("provider") != provider_name or not hmac.compare_digest(
        hash_token(binder), str(transaction.get("binder_hash", ""))
    ):
        return _failure(request)
    try:
        id_token = exchange_code(
            provider, code, str(transaction["verifier"]), _fetch(request)
        )
        claims = _verifier(request)(
            provider, id_token, str(transaction["nonce"]), _fetch(request)
        )
    except (KeyError, OSError, ValueError):
        return _failure(request)
    subject = str(claims.get("sub", ""))
    email = str(claims.get("email", "")).strip().casefold()
    if not subject or not email or claims.get("email_verified") is not True:
        return _failure(request)
    store = request.app.state.auth_store
    user_id = store.get_oidc_user_id(provider.issuer, subject)
    user = store.get_user_by_id(user_id) if user_id else None
    if user is None:
        if store.get_user_by_email(email) is not None:
            return _failure(request)  # never link an existing account by email alone
        user = UserRecord(id=uuid.uuid4().hex, email=email, password_hash="oidc-only")
        try:
            store.save_user(user)
        except DuplicateUserError:
            return _failure(request)
        store.save_oidc_identity(provider.issuer, subject, user.id)
    if user.totp_secret:
        nonce = stash_pending(request, user.id)
        response = redirect(f"/auth/totp/check?pending={nonce}")
    else:
        response = redirect("/")
        start_session(request, response, store, user)
    response.delete_cookie(
        OIDC_COOKIE,
        httponly=True,
        samesite="lax",
        secure=auth_config(request).secure_cookies,
        path="/auth/oidc",
    )
    return response

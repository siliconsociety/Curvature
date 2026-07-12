"""TOTP's orbit segment. The pending-login stash bridges password
success to code success: no session exists until both factors do."""

from __future__ import annotations

import json
import time
from typing import Annotated

from app.components.shell import shell
from fastapi import APIRouter, Form, Request
from satellites.auth.components.totp_desk import (
    TotpChallengeProps,
    TotpSetupProps,
    totp_challenge,
    totp_setup,
)
from satellites.auth.security import (
    hash_token,
    match_totp_counter,
    new_session_token,
    new_totp_secret,
    otpauth_uri,
)
from satellites.auth.sessions import (
    CurrentUser,
    rate_limit,
    require_write_origin,
    start_session,
)
from satellites.auth.store import ChallengeRecord

from curvature import redirect, respond

router = APIRouter()

PENDING_SECONDS = 300
PENDING_ATTEMPTS = 5


def stash_pending(request: Request, user_id: str, attempts: int = PENDING_ATTEMPTS) -> str:
    nonce = new_session_token()
    request.app.state.auth_store.save_challenge(ChallengeRecord(
        token_hash=hash_token(nonce),
        kind="totp-login",
        payload=json.dumps({"user_id": user_id, "attempts": attempts}),
        expires_at=time.time() + PENDING_SECONDS,
    ))
    return nonce


def pop_pending(request: Request, nonce: str) -> tuple[str, int] | None:
    challenge = request.app.state.auth_store.pop_challenge(
        hash_token(nonce), "totp-login", time.time()
    )
    if challenge is None:
        return None
    payload = json.loads(challenge.payload)
    return str(payload["user_id"]), int(payload["attempts"])


@router.get("/totp")
def totp_setup_page(request: Request, user: CurrentUser):
    secret = new_totp_secret()
    return respond(
        request,
        totp_setup(TotpSetupProps(
            secret=secret,
            uri=otpauth_uri(secret, user.email, request.app.title),
        )),
        shell=shell,
        purpose="Set up two-factor: bind an authenticator secret by proving one "
                "code; the secret binds only after the proof.",
    )


@router.post("/totp/enable")
def totp_enable(
    request: Request,
    user: CurrentUser,
    secret: Annotated[str, Form()],
    code: Annotated[str, Form()],
):
    counter = match_totp_counter(secret, code)
    if counter is None:
        return redirect("/auth/totp")
    store = request.app.state.auth_store
    store.set_totp_secret(user.id, secret)
    store.claim_totp_counter(user.id, counter)
    return redirect("/")


@router.get("/totp/check")
def totp_check_page(request: Request, pending: str = "", error: str = ""):
    return respond(
        request,
        totp_challenge(TotpChallengeProps(pending=pending, error=error or None)),
        shell=shell,
        purpose="Second factor: one authenticator code completes the sign-in "
                "the password began.",
    )


@router.post("/totp/check")
def totp_check(
    request: Request,
    pending: Annotated[str, Form()],
    code: Annotated[str, Form()],
):
    require_write_origin(request)
    pending_login = pop_pending(request, pending)
    user_id, attempts = pending_login if pending_login else (None, 0)
    store = request.app.state.auth_store
    user = store.get_user_by_id(user_id) if user_id else None
    if user is None:
        return redirect("/auth/login?error=credentials")
    rate_limit(request, "totp", user.id, limit=10, window_seconds=600)
    counter = match_totp_counter(user.totp_secret, code) if user.totp_secret else None
    if counter is None or not store.claim_totp_counter(user.id, counter):
        if attempts <= 1:
            return redirect("/auth/login?error=credentials")
        nonce = stash_pending(request, user.id, attempts - 1)
        return redirect(f"/auth/totp/check?pending={nonce}&error=code")
    response = redirect("/")
    start_session(request, response, store, user)
    return response


@router.post("/totp/disable")
def totp_disable(
    request: Request, user: CurrentUser, code: Annotated[str, Form()]
):
    store = request.app.state.auth_store
    counter = match_totp_counter(user.totp_secret, code) if user.totp_secret else None
    if counter is not None and store.claim_totp_counter(user.id, counter):
        store.set_totp_secret(user.id, None)
    return redirect("/")

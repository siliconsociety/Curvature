"""TOTP's orbit segment. The pending-login stash bridges password
success to code success: no session exists until both factors do."""

from __future__ import annotations

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
    new_session_token,
    new_totp_secret,
    otpauth_uri,
    verify_totp,
)
from satellites.auth.sessions import CurrentUser, start_session

from curvature import redirect, respond

router = APIRouter()

PENDING_SECONDS = 300


def pending_logins(request: Request) -> dict[str, tuple[str, float]]:
    stash = getattr(request.app.state, "auth_pending_logins", None)
    if stash is None:
        stash = {}
        request.app.state.auth_pending_logins = stash
    return stash


def stash_pending(request: Request, user_id: str) -> str:
    nonce = new_session_token()[:16]
    pending_logins(request)[nonce] = (user_id, time.time() + PENDING_SECONDS)
    return nonce


def pop_pending(request: Request, nonce: str) -> str | None:
    user_id, expires = pending_logins(request).pop(nonce, (None, 0))
    return user_id if user_id and expires > time.time() else None


@router.get("/totp")
async def totp_setup_page(request: Request, user: CurrentUser):
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
async def totp_enable(
    request: Request,
    user: CurrentUser,
    secret: Annotated[str, Form()],
    code: Annotated[str, Form()],
):
    if not verify_totp(secret, code):
        return redirect("/auth/totp")
    request.app.state.auth_store.set_totp_secret(user.id, secret)
    return redirect("/")


@router.get("/totp/check")
async def totp_check_page(request: Request, pending: str = "", error: str = ""):
    return respond(
        request,
        totp_challenge(TotpChallengeProps(pending=pending, error=error or None)),
        shell=shell,
        purpose="Second factor: one authenticator code completes the sign-in "
                "the password began.",
    )


@router.post("/totp/check")
async def totp_check(
    request: Request,
    pending: Annotated[str, Form()],
    code: Annotated[str, Form()],
):
    user_id = pop_pending(request, pending)
    store = request.app.state.auth_store
    user = store.get_user_by_id(user_id) if user_id else None
    if user is None:
        return redirect("/auth/login?error=credentials")
    if not user.totp_secret or not verify_totp(user.totp_secret, code):
        nonce = stash_pending(request, user.id)
        return redirect(f"/auth/totp/check?pending={nonce}&error=code")
    response = redirect("/")
    start_session(response, store, user)
    return response


@router.post("/totp/disable")
async def totp_disable(
    request: Request, user: CurrentUser, code: Annotated[str, Form()]
):
    if user.totp_secret and verify_totp(user.totp_secret, code):
        request.app.state.auth_store.set_totp_secret(user.id, None)
    return redirect("/")

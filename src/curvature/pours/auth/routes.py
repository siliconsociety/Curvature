"""Auth's orbit: reads render, writes redirect, errors ride the query
string. The satellite borrows YOUR shell — it's your code now."""

from __future__ import annotations

import json
import time
import urllib.parse
import uuid
from typing import Annotated

from app.components.shell import shell
from fastapi import APIRouter, Form, Request
from satellites.auth.components.auth_forms import (
    LoginFormProps,
    RegisterFormProps,
    login_form,
    register_form,
)
from satellites.auth.components.token_desk import TokenDeskProps, token_desk
from satellites.auth.routes_totp import stash_pending
from satellites.auth.security import (
    hash_password,
    hash_token,
    new_session_token,
    verify_password,
)
from satellites.auth.sessions import (
    CurrentUser,
    auth_config,
    end_session,
    rate_limit,
    require_write_origin,
    start_session,
)
from satellites.auth.store import ChallengeRecord, DuplicateUserError, TokenRecord, UserRecord

from curvature import redirect, respond

router = APIRouter()
REVEAL_SECONDS = 120
DUMMY_PASSWORD_HASH = hash_password(new_session_token())


def _location(path: str, **query: str) -> str:
    return f"{path}?{urllib.parse.urlencode(query)}"


def _email(value: str) -> str | None:
    address = value.strip().casefold()
    if len(address) > 254 or address.count("@") != 1:
        return None
    local, domain = address.split("@")
    return address if local and "." in domain and not domain.startswith(".") else None


@router.get("/login")
def login_page(request: Request, error: str | None = None, email: str = ""):
    providers = tuple(getattr(request.app.state, "auth_oidc", {}))
    props = LoginFormProps(error=error, email=email, providers=providers)
    return respond(
        request, login_form(props), shell=shell,
        purpose="Sign in with email and password to act as yourself here.",
    )


@router.post("/login")
def login(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    require_write_origin(request)
    address = _email(email)
    rate_limit(request, "login", address or email[:254], limit=10, window_seconds=600)
    store = request.app.state.auth_store
    user = store.get_user_by_email(address) if address else None
    valid = verify_password(password[:1024], user.password_hash if user else DUMMY_PASSWORD_HASH)
    if user is None or not valid:
        return redirect(_location("/auth/login", error="credentials", email=address or ""))
    if user.totp_secret:
        nonce = stash_pending(request, user.id)
        return redirect(f"/auth/totp/check?pending={nonce}")
    response = redirect("/")
    start_session(request, response, store, user)
    return response


@router.get("/register")
def register_page(request: Request, error: str | None = None, email: str = ""):
    props = RegisterFormProps(error=error, email=email)
    return respond(
        request, register_form(props), shell=shell,
        purpose="Create an account: an email and a password of 8+ characters.",
    )


@router.post("/register")
def register(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    require_write_origin(request)
    store = request.app.state.auth_store
    address = _email(email)
    rate_limit(request, "register", address or email[:254], limit=5, window_seconds=3600)
    if address is None:
        return redirect(_location("/auth/register", error="email-invalid", email=""))
    if len(password) < 12 or len(password) > 1024:
        return redirect(_location("/auth/register", error="password-short", email=address))
    if store.get_user_by_email(address) is not None:
        return redirect(_location("/auth/register", error="email-taken", email=address))
    user = UserRecord(
        id=uuid.uuid4().hex, email=address, password_hash=hash_password(password)
    )
    try:
        store.save_user(user)
    except DuplicateUserError:
        return redirect(_location("/auth/register", error="email-taken", email=address))
    response = redirect("/")
    start_session(request, response, store, user)
    return response


@router.post("/logout")
def logout(request: Request, _user: CurrentUser):
    store = request.app.state.auth_store
    response = redirect("/")
    end_session(request, response, store)
    return response


@router.get("/tokens")
def tokens_page(request: Request, user: CurrentUser, reveal: str = ""):
    store = request.app.state.auth_store
    store.purge_expired(time.time())
    challenge = (
        store.pop_challenge(hash_token(reveal), "token-reveal", time.time()) if reveal else None
    )
    payload = json.loads(challenge.payload) if challenge else {}
    revealed = payload.get("token") if payload.get("user_id") == user.id else None
    return respond(
        request,
        token_desk(TokenDeskProps(
            tokens=tuple(store.list_tokens(user.id)), revealed=revealed,
        )),
        shell=shell,
        purpose="Mint or revoke personal access tokens: credentials a human "
                "hands their agent to act with the human's own authority.",
    )


@router.post("/tokens")
def mint_token(request: Request, user: CurrentUser, label: Annotated[str, Form()]):
    token = new_session_token()
    store = request.app.state.auth_store
    expires_at = time.time() + auth_config(request).token_seconds
    store.save_token(TokenRecord(
        token_hash=hash_token(token),
        user_id=user.id,
        label=(label.strip() or "unlabeled")[:60],
        expires_at=expires_at,
    ))
    nonce = new_session_token()
    store.save_challenge(ChallengeRecord(
        token_hash=hash_token(nonce),
        kind="token-reveal",
        payload=json.dumps({"user_id": user.id, "token": token}),
        expires_at=time.time() + REVEAL_SECONDS,
    ))
    return redirect(f"/auth/tokens?reveal={nonce}")


@router.post("/tokens/revoke")
def revoke_token(
    request: Request, user: CurrentUser, token_hash: Annotated[str, Form()]
):
    request.app.state.auth_store.delete_token(token_hash, user.id)
    return redirect("/auth/tokens")

"""Auth's orbit: reads render, writes redirect, errors ride the query
string. The satellite borrows YOUR shell — it's your code now."""

from __future__ import annotations

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
from satellites.auth.security import (
    hash_password,
    hash_token,
    new_session_token,
    verify_password,
)
from satellites.auth.sessions import CurrentUser, end_session, start_session
from satellites.auth.store import TokenRecord, UserRecord

from curvature import redirect, respond

router = APIRouter()


@router.get("/login")
async def login_page(request: Request, error: str | None = None, email: str = ""):
    props = LoginFormProps(error=error, email=email)
    return respond(
        request, login_form(props), shell=shell,
        purpose="Sign in with email and password to act as yourself here.",
    )


@router.post("/login")
async def login(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    store = request.app.state.auth_store
    user = store.get_user_by_email(email.strip().lower())
    if user is None or not verify_password(password, user.password_hash):
        return redirect(f"/auth/login?error=credentials&email={email.strip().lower()}")
    response = redirect("/")
    start_session(response, store, user)
    return response


@router.get("/register")
async def register_page(request: Request, error: str | None = None, email: str = ""):
    props = RegisterFormProps(error=error, email=email)
    return respond(
        request, register_form(props), shell=shell,
        purpose="Create an account: an email and a password of 8+ characters.",
    )


@router.post("/register")
async def register(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    store = request.app.state.auth_store
    address = email.strip().lower()
    if len(password) < 8:
        return redirect(f"/auth/register?error=password-short&email={address}")
    if store.get_user_by_email(address) is not None:
        return redirect(f"/auth/register?error=email-taken&email={address}")
    user = UserRecord(
        id=uuid.uuid4().hex, email=address, password_hash=hash_password(password)
    )
    store.save_user(user)
    response = redirect("/")
    start_session(response, store, user)
    return response


@router.post("/logout")
async def logout(request: Request, _user: CurrentUser):
    store = request.app.state.auth_store
    response = redirect("/")
    end_session(request, response, store)
    return response


def _reveals(request: Request) -> dict[str, str]:
    stash = getattr(request.app.state, "auth_token_reveals", None)
    if stash is None:
        stash = {}
        request.app.state.auth_token_reveals = stash
    return stash


@router.get("/tokens")
async def tokens_page(request: Request, user: CurrentUser, reveal: str = ""):
    revealed = _reveals(request).pop(reveal, None) if reveal else None
    store = request.app.state.auth_store
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
async def mint_token(request: Request, user: CurrentUser, label: Annotated[str, Form()]):
    token = new_session_token()
    store = request.app.state.auth_store
    store.save_token(TokenRecord(
        token_hash=hash_token(token), user_id=user.id, label=label.strip() or "unlabeled",
    ))
    nonce = new_session_token()[:16]
    _reveals(request)[nonce] = token
    return redirect(f"/auth/tokens?reveal={nonce}")


@router.post("/tokens/revoke")
async def revoke_token(
    request: Request, user: CurrentUser, token_hash: Annotated[str, Form()]
):
    request.app.state.auth_store.delete_token(token_hash, user.id)
    return redirect("/auth/tokens")

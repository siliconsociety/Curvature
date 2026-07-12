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
from satellites.auth.security import hash_password, verify_password
from satellites.auth.sessions import CurrentUser, end_session, start_session
from satellites.auth.store import UserRecord

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

"""Auth's faces: real forms, errors carried by query param so every
write stays POST -> redirect -> GET (C-201). No client state, ever."""

from __future__ import annotations

from curvature import Element, Props
from curvature import html as h

ERRORS = {
    "credentials": "That email and password don't match our records.",
    "email-invalid": "Enter a complete email address.",
    "email-taken": "An account with that email already exists.",
    "password-short": "Passwords need 12 to 1024 characters.",
}


class LoginFormProps(Props):
    error: str | None = None
    email: str = ""
    providers: tuple[str, ...] = ()


class RegisterFormProps(Props):
    error: str | None = None
    email: str = ""


def _error_line(error: str | None) -> Element | None:
    if error is None:
        return None
    return h.p(ERRORS.get(error, "Something went sideways; try again."), class_="auth-error")


def login_form(props: LoginFormProps) -> Element:
    return h.section(
        h.h2("Sign in"),
        _error_line(props.error),
        h.form(
            h.label("Email", for_="email"),
            h.input_(type="email", name="email", id="email",
                     value=props.email, required=True, autocomplete="email"),
            h.label("Password", for_="password"),
            h.input_(type="password", name="password", id="password",
                     required=True, autocomplete="current-password"),
            h.button("Sign in", class_="auth-submit"),
            action="/auth/login",
            method="post",
            class_="auth-form",
        ),
        h.p(h.a("Need an account? Register", href="/auth/register")),
        h.nav(
            (
                h.a(f"Sign in with {name.title()}",
                    href=f"/auth/oidc/{name}/login", class_="oidc-link")
                for name in props.providers
            ),
            class_="oidc-links",
        ) if props.providers else None,
        id="auth-login",
    )


def register_form(props: RegisterFormProps) -> Element:
    return h.section(
        h.h2("Create your account"),
        _error_line(props.error),
        h.form(
            h.label("Email", for_="email"),
            h.input_(type="email", name="email", id="email",
                     value=props.email, required=True, autocomplete="email"),
            h.label("Password", for_="password"),
            h.input_(type="password", name="password", id="password",
                     required=True, minlength=12, maxlength=1024,
                     autocomplete="new-password"),
            h.button("Register", class_="auth-submit"),
            action="/auth/register",
            method="post",
            class_="auth-form",
        ),
        h.p(h.a("Already aboard? Sign in", href="/auth/login")),
        id="auth-register",
    )

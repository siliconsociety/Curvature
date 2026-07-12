"""TOTP's faces: setup (secret shown once, verified before it binds),
the login challenge, and the disable form. Pure forms, zero JS, and
the secret travels as copyable text — the otpauth URI works by hand in
any authenticator, no QR dependency required."""

from __future__ import annotations

from curvature import Element, Props
from curvature import html as h


class TotpSetupProps(Props):
    secret: str
    uri: str
    error: str | None = None


class TotpChallengeProps(Props):
    pending: str
    error: str | None = None


class TotpStatusProps(Props):
    enabled: bool


def totp_setup(props: TotpSetupProps) -> Element:
    return h.section(
        h.h2("Set up two-factor"),
        h.p("Add this secret to your authenticator, then prove it once:"),
        h.p(h.code(props.secret, class_="totp-secret")),
        h.p(h.code(props.uri, class_="totp-uri")),
        h.p("The code didn't match — mind the clock.", class_="auth-error")
        if props.error else None,
        h.form(
            h.input_(type="hidden", name="secret", value=props.secret),
            h.label("Code from your app", for_="code"),
            h.input_(type="text", name="code", id="code", required=True,
                     minlength=6, maxlength=6, autocomplete="one-time-code"),
            h.button("Enable", class_="auth-submit"),
            action="/auth/totp/enable",
            method="post",
            class_="auth-form",
        ),
        id="totp-setup",
    )


def totp_challenge(props: TotpChallengeProps) -> Element:
    return h.section(
        h.h2("Second factor"),
        h.p("Wrong code — try the next one.", class_="auth-error")
        if props.error else None,
        h.form(
            h.input_(type="hidden", name="pending", value=props.pending),
            h.label("Code from your app", for_="code"),
            h.input_(type="text", name="code", id="code", required=True,
                     minlength=6, maxlength=6, autocomplete="one-time-code"),
            h.button("Verify", class_="auth-submit"),
            action="/auth/totp/check",
            method="post",
            class_="auth-form",
        ),
        id="totp-challenge",
    )


def totp_status(props: TotpStatusProps) -> Element:
    if not props.enabled:
        return h.section(
            h.p(h.a("Set up two-factor authentication", href="/auth/totp")),
            id="totp-status",
        )
    return h.section(
        h.p("Two-factor is on."),
        h.form(
            h.label("Code to confirm", for_="code"),
            h.input_(type="text", name="code", id="code", required=True,
                     minlength=6, maxlength=6, autocomplete="one-time-code"),
            h.button("Disable two-factor", class_="auth-submit"),
            action="/auth/totp/disable",
            method="post",
            class_="auth-form",
        ),
        id="totp-status",
    )

"""The token desk: where a human mints borrowed authority for their
agents. The token is shown exactly once, then only its hash exists."""

from __future__ import annotations

from satellites.auth.store import TokenRecord

from curvature import Element, Props
from curvature import html as h


class TokenDeskProps(Props):
    tokens: tuple[TokenRecord, ...]
    revealed: str | None = None


class TokenRowProps(Props):
    token: TokenRecord


def _token_row(props: TokenRowProps) -> Element:
    token = props.token
    return h.li(
        h.span(token.label, class_="token-label"),
        h.form(
            h.input_(type="hidden", name="token_hash", value=token.token_hash),
            h.button("Revoke", class_="token-revoke"),
            action="/auth/tokens/revoke",
            method="post",
            class_="token-revoke-form",
        ),
        class_="token",
    )


def token_desk(props: TokenDeskProps) -> Element:
    return h.section(
        h.h2("Agent tokens"),
        h.p(
            "Mint a token, hand it to your agent, and it acts as you — "
            "same permissions, no cookie, revocable here.",
        ),
        h.p(
            "Copy it now; it will not be shown again: ",
            h.code(props.revealed, class_="token-reveal"),
        ) if props.revealed else None,
        h.ul(
            (_token_row(TokenRowProps(token=token)) for token in props.tokens),
            class_="tokens",
        ) if props.tokens else h.p("No tokens minted.", class_="empty"),
        h.form(
            h.label("Label", for_="label"),
            h.input_(type="text", name="label", id="label",
                     required=True, maxlength=60,
                     placeholder="e.g. laptop assistant"),
            h.button("Mint token", class_="token-mint"),
            action="/auth/tokens",
            method="post",
            class_="token-mint-form",
        ),
        id="auth-tokens",
    )

"""Direct OIDC — one standard, zero middlemen (the Auth position).

Any issuer that speaks the well-known discovery document works: Google,
Microsoft, Apple, your homelab. The app assembly declares providers
explicitly; nothing is discovered that wasn't configured:

    from satellites.auth.oidc import OIDCProvider

    app.state.auth_oidc = {
        "google": OIDCProvider(
            issuer="https://accounts.google.com",
            client_id="...",
            client_secret="...",
            redirect_uri="https://your.app/auth/oidc/google/callback",
        ),
    }

Requires PyJWT for id_token verification: `uv add pyjwt` (with
`pyjwt[crypto]` for RS256 issuers, which is all the real ones).
SAML never enters the house; broker it to OIDC at the edge.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

type FetchJson = Callable[..., dict]


@dataclass(frozen=True)
class OIDCProvider:
    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = "openid email"


def _fetch_json(url: str, data: dict | None = None) -> dict:
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read())


def discover(provider: OIDCProvider, fetch: FetchJson = _fetch_json) -> dict:
    issuer = provider.issuer.rstrip("/")
    return fetch(f"{issuer}/.well-known/openid-configuration")


def authorization_url(provider: OIDCProvider, state: str,
                      fetch: FetchJson = _fetch_json) -> str:
    config = discover(provider, fetch)
    query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": provider.redirect_uri,
        "scope": provider.scope,
        "state": state,
    })
    return f"{config['authorization_endpoint']}?{query}"


def exchange_code(provider: OIDCProvider, code: str,
                  fetch: FetchJson = _fetch_json) -> str:
    config = discover(provider, fetch)
    payload = fetch(config["token_endpoint"], data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": provider.client_id,
        "client_secret": provider.client_secret,
        "redirect_uri": provider.redirect_uri,
    })
    return payload["id_token"]


def verify_id_token(provider: OIDCProvider, id_token: str,
                    fetch: FetchJson = _fetch_json) -> dict:
    """PyJWT against the issuer's published keys. A standard, assembled —
    never invented."""
    import jwt

    config = discover(provider, fetch)
    signing_key = jwt.PyJWKClient(config["jwks_uri"]).get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        audience=provider.client_id,
        issuer=provider.issuer,
    )

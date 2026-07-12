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

The Auth pour enables Curvature's `auth` extra, which supplies PyJWT with
its cryptography backend for RS256 and ES256 verification.
SAML never enters the house; broker it to OIDC at the edge.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
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
    config = fetch(f"{issuer}/.well-known/openid-configuration")
    if str(config.get("issuer", issuer)).rstrip("/") != issuer:
        raise ValueError("OIDC discovery issuer does not match configured issuer")
    return config


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def authorization_url(provider: OIDCProvider, state: str, nonce: str, code_challenge: str,
                      fetch: FetchJson = _fetch_json) -> str:
    config = discover(provider, fetch)
    query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": provider.redirect_uri,
        "scope": provider.scope,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    return f"{config['authorization_endpoint']}?{query}"


def exchange_code(provider: OIDCProvider, code: str, code_verifier: str,
                  fetch: FetchJson = _fetch_json) -> str:
    config = discover(provider, fetch)
    payload = fetch(config["token_endpoint"], data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": provider.client_id,
        "client_secret": provider.client_secret,
        "redirect_uri": provider.redirect_uri,
        "code_verifier": code_verifier,
    })
    return payload["id_token"]


def verify_id_token(provider: OIDCProvider, id_token: str, expected_nonce: str,
                    fetch: FetchJson = _fetch_json) -> dict:
    """PyJWT against the issuer's published keys. A standard, assembled —
    never invented."""
    import jwt

    config = discover(provider, fetch)
    header = jwt.get_unverified_header(id_token)
    key_set = jwt.PyJWKSet.from_dict(fetch(config["jwks_uri"]))
    signing_key = next((key for key in key_set.keys if key.key_id == header.get("kid")), None)
    if signing_key is None:
        raise ValueError("OIDC signing key not found")
    supported = config.get("id_token_signing_alg_values_supported", ["RS256", "ES256"])
    algorithms = [algorithm for algorithm in supported if algorithm in {"RS256", "ES256"}]
    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=algorithms,
        audience=provider.client_id,
        issuer=provider.issuer,
    )
    if not hmac.compare_digest(str(claims.get("nonce", "")), expected_nonce):
        raise ValueError("OIDC nonce does not match")
    return claims

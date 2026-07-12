"""Poured with the Auth satellite: the second factor and the federated
door. Same law as the first file — no session until every owed factor
is paid."""

import json
import re
import time

import pytest
from app.main import app
from fastapi.testclient import TestClient
from satellites.auth.security import totp_code
from satellites.auth.sessions import SESSION_COOKIE, AuthConfig


@pytest.fixture
def client(tmp_path):
    from satellites.auth.store_sqlite import SqliteAuthStore

    app.state.auth_store = SqliteAuthStore(tmp_path / "auth.db")
    app.state.auth_config = AuthConfig.testing()
    return TestClient(app, headers={"origin": "http://testserver"})


def register(client, email="two@factor.example", password="pit-wall-radio"):
    return client.post(
        "/auth/register", data={"email": email, "password": password},
        follow_redirects=False,
    )


def enable_totp(client):
    register(client)
    setup = client.get("/auth/totp").text
    match = re.search(r'name="secret" value="([^"]+)"', setup)
    assert match is not None
    secret = match.group(1)
    client.post("/auth/totp/enable", data={"secret": secret, "code": totp_code(secret)})
    return secret


# --- TOTP ----------------------------------------------------------------------


def test_totp_binds_only_after_proof(client):
    register(client)
    setup = client.get("/auth/totp").text
    match = re.search(r'name="secret" value="([^"]+)"', setup)
    assert match is not None
    secret = match.group(1)
    response = client.post(
        "/auth/totp/enable", data={"secret": secret, "code": "000000"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/auth/totp"  # wrong code: no bind
    user = client.app.state.auth_store.get_user_by_email("two@factor.example")
    assert user.totp_secret is None


def test_login_with_totp_demands_the_second_factor(client):
    secret = enable_totp(client)
    client.cookies.clear()
    response = client.post(
        "/auth/login",
        data={"email": "two@factor.example", "password": "pit-wall-radio"},
        follow_redirects=False,
    )
    assert "/auth/totp/check" in response.headers["location"]
    assert SESSION_COOKIE not in response.cookies  # password alone earns nothing
    pending = response.headers["location"].split("pending=")[1].split("&")[0]
    wrong = client.post(
        "/auth/totp/check", data={"pending": pending, "code": "000000"},
        follow_redirects=False,
    )
    assert SESSION_COOKIE not in wrong.cookies
    pending = wrong.headers["location"].split("pending=")[1].split("&")[0]
    right = client.post(
        "/auth/totp/check",
        data={"pending": pending, "code": totp_code(secret, time.time() + 30)},
        follow_redirects=False,
    )
    assert SESSION_COOKIE in right.cookies  # both factors, one session


def test_stale_pending_nonces_die(client):
    response = client.post(
        "/auth/totp/check", data={"pending": "expired-or-fake", "code": "123456"},
        follow_redirects=False,
    )
    assert "error=credentials" in response.headers["location"]


# --- OIDC ----------------------------------------------------------------------


def wire_fake_issuer(app, email="fed@example.com", *, email_verified=True):
    from satellites.auth.oidc import OIDCProvider

    app.state.auth_oidc = {"fake": OIDCProvider(
        issuer="https://fake.example",
        client_id="cid",
        client_secret="secret",
        redirect_uri="http://testserver/auth/oidc/fake/callback",
    )}

    def fake_fetch(url, data=None):
        if "well-known" in url:
            return {
                "issuer": "https://fake.example",
                "authorization_endpoint": "https://fake.example/authorize",
                "token_endpoint": "https://fake.example/token",
                "jwks_uri": "https://fake.example/jwks",
            }
        if url.endswith("/token"):
            assert data is not None
            assert data["grant_type"] == "authorization_code"
            assert data["code_verifier"]
            return {"id_token": "signed.by.the.issuer"}
        raise AssertionError(f"unexpected fetch: {url}")

    def fake_verify(provider, id_token, expected_nonce, fetch):
        assert id_token == "signed.by.the.issuer"
        assert expected_nonce
        return {
            "email": email,
            "email_verified": email_verified,
            "sub": "issuer-subject",
            "nonce": expected_nonce,
        }

    app.state.auth_oidc_fetch = fake_fetch
    app.state.auth_oidc_verify = fake_verify


def test_the_login_page_offers_configured_providers(client):
    wire_fake_issuer(client.app)
    text = client.get("/auth/login").text
    assert 'href="/auth/oidc/fake/login"' in text


def test_default_oidc_verifier_checks_the_published_key_and_nonce():
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from jwt.algorithms import RSAAlgorithm
    from satellites.auth.oidc import OIDCProvider, verify_id_token

    provider = OIDCProvider(
        issuer="https://issuer.example",
        client_id="curvature-client",
        client_secret="secret",
        redirect_uri="https://app.example/auth/callback",
    )
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "signing-key", "alg": "RS256", "use": "sig"})
    token = jwt.encode(
        {
            "iss": provider.issuer,
            "aud": provider.client_id,
            "sub": "subject-1",
            "nonce": "browser-nonce",
            "exp": int(time.time()) + 60,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "signing-key"},
    )

    def fetch(url, data=None):
        assert data is None
        if "well-known" in url:
            return {
                "issuer": provider.issuer,
                "jwks_uri": f"{provider.issuer}/jwks",
                "id_token_signing_alg_values_supported": ["RS256"],
            }
        return {"keys": [public_jwk]}

    claims = verify_id_token(provider, token, "browser-nonce", fetch)
    assert claims["sub"] == "subject-1"
    with pytest.raises(ValueError, match="nonce"):
        verify_id_token(provider, token, "wrong-nonce", fetch)


def test_oidc_round_trip_creates_and_signs_in(client):
    wire_fake_issuer(client.app)
    hop = client.get("/auth/oidc/fake/login", follow_redirects=False)
    location = hop.headers["location"]
    assert location.startswith("https://fake.example/authorize?")
    state = location.split("state=")[1].split("&")[0]
    back = client.get(
        f"/auth/oidc/fake/callback?code=authcode&state={state}",
        follow_redirects=False,
    )
    assert SESSION_COOKIE in back.cookies
    assert client.app.state.auth_store.get_user_by_email("fed@example.com") is not None


def test_oidc_state_is_bound_to_the_starting_browser(client):
    wire_fake_issuer(client.app)
    hop = client.get("/auth/oidc/fake/login", follow_redirects=False)
    state = hop.headers["location"].split("state=")[1].split("&")[0]
    client.cookies.clear()
    back = client.get(
        f"/auth/oidc/fake/callback?code=authcode&state={state}",
        follow_redirects=False,
    )
    assert "error=credentials" in back.headers["location"]
    assert SESSION_COOKIE not in back.cookies


def test_oidc_refuses_forged_state(client):
    wire_fake_issuer(client.app)
    back = client.get(
        "/auth/oidc/fake/callback?code=authcode&state=forged",
        follow_redirects=False,
    )
    assert "error=credentials" in back.headers["location"]
    assert SESSION_COOKIE not in back.cookies


def test_oidc_refuses_unverified_email_claims(client):
    wire_fake_issuer(client.app, email_verified=False)
    hop = client.get("/auth/oidc/fake/login", follow_redirects=False)
    state = hop.headers["location"].split("state=")[1].split("&")[0]
    back = client.get(
        f"/auth/oidc/fake/callback?code=authcode&state={state}",
        follow_redirects=False,
    )
    assert "error=credentials" in back.headers["location"]
    assert SESSION_COOKIE not in back.cookies


def test_oidc_never_links_an_existing_account_by_email(client):
    register(client, email="local@account.example")
    client.cookies.clear()
    wire_fake_issuer(client.app, email="local@account.example")
    hop = client.get("/auth/oidc/fake/login", follow_redirects=False)
    state = hop.headers["location"].split("state=")[1].split("&")[0]
    back = client.get(
        f"/auth/oidc/fake/callback?code=authcode&state={state}",
        follow_redirects=False,
    )
    assert "error=credentials" in back.headers["location"]
    assert SESSION_COOKIE not in back.cookies


def test_totp_challenges_have_a_finite_attempt_budget(client):
    enable_totp(client)
    client.cookies.clear()
    response = client.post(
        "/auth/login",
        data={"email": "two@factor.example", "password": "pit-wall-radio"},
        follow_redirects=False,
    )
    pending = response.headers["location"].split("pending=")[1]
    for _attempt in range(4):
        response = client.post(
            "/auth/totp/check", data={"pending": pending, "code": "000000"},
            follow_redirects=False,
        )
        pending = response.headers["location"].split("pending=")[1].split("&")[0]
    response = client.post(
        "/auth/totp/check", data={"pending": pending, "code": "000000"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/auth/login?error=credentials"
    assert SESSION_COOKIE not in response.cookies


def test_federated_users_with_totp_still_owe_the_code(client):
    wire_fake_issuer(client.app, email="two@factor.example")
    hop = client.get("/auth/oidc/fake/login", follow_redirects=False)
    state = hop.headers["location"].split("state=")[1].split("&")[0]
    client.get(
        f"/auth/oidc/fake/callback?code=authcode&state={state}", follow_redirects=False,
    )
    secret = enable_totp(client)
    client.cookies.clear()
    hop = client.get("/auth/oidc/fake/login", follow_redirects=False)
    state = hop.headers["location"].split("state=")[1].split("&")[0]
    back = client.get(
        f"/auth/oidc/fake/callback?code=authcode&state={state}",
        follow_redirects=False,
    )
    assert SESSION_COOKIE not in back.cookies
    assert "/auth/totp/check" in back.headers["location"]
    pending = back.headers["location"].split("pending=")[1].split("&")[0]
    done = client.post(
        "/auth/totp/check",
        data={"pending": pending, "code": totp_code(secret, time.time() + 30)},
        follow_redirects=False,
    )
    assert SESSION_COOKIE in done.cookies

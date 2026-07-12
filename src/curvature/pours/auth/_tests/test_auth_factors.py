"""Poured with the Auth satellite: the second factor and the federated
door. Same law as the first file — no session until every owed factor
is paid."""

import re

import pytest
from app.main import app
from fastapi.testclient import TestClient
from satellites.auth.security import totp_code
from satellites.auth.sessions import SESSION_COOKIE


@pytest.fixture
def client(tmp_path):
    from satellites.auth.store_sqlite import SqliteAuthStore

    app.state.auth_store = SqliteAuthStore(tmp_path / "auth.db")
    app.state.auth_pending_logins = {}
    app.state.auth_oidc_states = {}
    return TestClient(app)


def register(client, email="two@factor.example", password="pit-wall-radio"):
    return client.post(
        "/auth/register", data={"email": email, "password": password},
        follow_redirects=False,
    )


def enable_totp(client):
    register(client)
    setup = client.get("/auth/totp").text
    secret = re.search(r'name="secret" value="([^"]+)"', setup).group(1)
    client.post("/auth/totp/enable", data={"secret": secret, "code": totp_code(secret)})
    return secret


# --- TOTP ----------------------------------------------------------------------


def test_totp_binds_only_after_proof(client):
    register(client)
    setup = client.get("/auth/totp").text
    secret = re.search(r'name="secret" value="([^"]+)"', setup).group(1)
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
        "/auth/totp/check", data={"pending": pending, "code": totp_code(secret)},
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


def wire_fake_issuer(app, email="fed@example.com"):
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
                "authorization_endpoint": "https://fake.example/authorize",
                "token_endpoint": "https://fake.example/token",
                "jwks_uri": "https://fake.example/jwks",
            }
        if url.endswith("/token"):
            assert data["grant_type"] == "authorization_code"
            return {"id_token": "signed.by.the.issuer"}
        raise AssertionError(f"unexpected fetch: {url}")

    def fake_verify(provider, id_token, fetch):
        assert id_token == "signed.by.the.issuer"
        return {"email": email, "sub": "issuer-subject"}

    app.state.auth_oidc_fetch = fake_fetch
    app.state.auth_oidc_verify = fake_verify


def test_the_login_page_offers_configured_providers(client):
    wire_fake_issuer(client.app)
    text = client.get("/auth/login").text
    assert 'href="/auth/oidc/fake/login"' in text


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


def test_oidc_refuses_forged_state(client):
    wire_fake_issuer(client.app)
    back = client.get(
        "/auth/oidc/fake/callback?code=authcode&state=forged",
        follow_redirects=False,
    )
    assert "error=credentials" in back.headers["location"]
    assert SESSION_COOKIE not in back.cookies


def test_federated_users_with_totp_still_owe_the_code(client):
    wire_fake_issuer(client.app, email="two@factor.example")
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
        "/auth/totp/check", data={"pending": pending, "code": totp_code(secret)},
        follow_redirects=False,
    )
    assert SESSION_COOKIE in done.cookies

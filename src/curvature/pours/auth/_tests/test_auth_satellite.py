"""Poured with the Auth satellite. These tests are the no-JS user
driving real forms — and the C-203 probe attacking from another origin."""

import pytest
from app.main import app
from fastapi.testclient import TestClient
from satellites.auth.sessions import SESSION_COOKIE


@pytest.fixture
def client(tmp_path):
    from satellites.auth.store_sqlite import SqliteAuthStore

    app.state.auth_store = SqliteAuthStore(tmp_path / "auth.db")
    return TestClient(app)


def register(client, email="pit@crew.example", password="fresh-tires-88"):
    return client.post(
        "/auth/register", data={"email": email, "password": password},
        follow_redirects=False,
    )


def test_register_sets_a_session_and_redirects(client):
    response = register(client)
    assert response.status_code == 303
    assert SESSION_COOKIE in response.cookies
    cookie_header = response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header and "samesite=lax" in cookie_header


def test_short_passwords_bounce_with_the_reason_in_the_url(client):
    response = client.post(
        "/auth/register", data={"email": "a@b.example", "password": "short"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=password-short" in response.headers["location"]


def test_duplicate_email_bounces(client):
    register(client)
    response = register(client)
    assert "error=email-taken" in response.headers["location"]


def test_login_round_trip(client):
    register(client)
    client.cookies.clear()
    response = client.post(
        "/auth/login", data={"email": "pit@crew.example", "password": "fresh-tires-88"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert SESSION_COOKIE in response.cookies


def test_wrong_password_bounces_without_a_cookie(client):
    register(client)
    client.cookies.clear()
    response = client.post(
        "/auth/login", data={"email": "pit@crew.example", "password": "wrong-tires"},
        follow_redirects=False,
    )
    assert "error=credentials" in response.headers["location"]
    assert SESSION_COOKIE not in response.cookies


def test_logout_ends_the_session(client):
    register(client)
    response = client.post("/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    followed = client.post("/auth/logout", follow_redirects=False)
    assert followed.status_code == 303  # idempotent; no session required


def test_cross_origin_writes_are_refused_c203(client):
    register(client)
    response = client.post(
        "/auth/logout",
        headers={"origin": "https://evil.example"},
        follow_redirects=False,
    )
    # The session dependency refuses before the handler runs: a foreign
    # Origin with a riding cookie is exactly the CSRF shape.
    assert response.status_code == 403


def test_login_page_is_a_real_form_js_off(client):
    text = client.get("/auth/login").text
    assert 'action="/auth/login"' in text
    assert 'method="post"' in text
    assert text.startswith("<!doctype html>")


def mint(client, label="laptop assistant"):
    register(client)
    response = client.post(
        "/auth/tokens", data={"label": label}, follow_redirects=False
    )
    reveal_url = response.headers["location"]
    page = client.get(reveal_url).text
    import re

    return re.search(r'<code class="token-reveal">([^<]+)</code>', page).group(1)


def test_minted_tokens_are_shown_exactly_once(client):
    register(client)
    response = client.post(
        "/auth/tokens", data={"label": "one-shot"}, follow_redirects=False
    )
    reveal_url = response.headers["location"]
    first = client.get(reveal_url).text
    assert "Copy it now" in first
    second = client.get(reveal_url).text
    assert "Copy it now" not in second  # the nonce is consumed


def test_a_bearer_agent_acts_as_its_human(client):
    token = mint(client)
    client.cookies.clear()  # the agent has no cookies, only the token
    page = client.get("/auth/tokens", headers={"Authorization": f"Bearer {token}"})
    assert page.status_code == 200
    assert "laptop assistant" in page.text


def test_bearer_writes_skip_c203_by_design(client):
    token = mint(client)
    client.cookies.clear()
    response = client.post(
        "/auth/tokens",
        data={"label": "minted by an agent"},
        headers={"Authorization": f"Bearer {token}", "origin": "https://far.example"},
        follow_redirects=False,
    )
    assert response.status_code == 303  # no cookie rides, no CSRF shape


def test_revoked_tokens_die(client):
    from satellites.auth.security import hash_token

    token = mint(client)
    client.post("/auth/tokens/revoke", data={"token_hash": hash_token(token)})
    client.cookies.clear()
    response = client.get(
        "/auth/tokens", headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert response.status_code == 303  # bounced to login: the authority is gone


def test_bogus_bearer_tokens_are_nobody(client):
    client.cookies.clear()
    response = client.get(
        "/auth/tokens", headers={"Authorization": "Bearer counterfeit"},
        follow_redirects=False,
    )
    assert response.status_code == 303

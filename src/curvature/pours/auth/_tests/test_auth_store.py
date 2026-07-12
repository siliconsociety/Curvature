"""The shared SQLite control plane: atomic across workers, bounded in time."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from satellites.auth.store import (
    ChallengeRecord,
    DuplicateUserError,
    SessionRecord,
    TokenRecord,
    UserRecord,
)
from satellites.auth.store_sqlite import SqliteAuthStore


@pytest.fixture
def store(tmp_path):
    return SqliteAuthStore(tmp_path / "auth.db")


def user(user_id="u1", email="pit@crew.example"):
    return UserRecord(id=user_id, email=email, password_hash="scrypt$x$y")


def test_identity_totp_session_and_token_lifecycle(store):
    store.save_user(user())
    assert store.get_user_by_email("pit@crew.example").id == "u1"
    store.set_totp_secret("u1", "SECRET")
    assert store.claim_totp_counter("u1", 10) is True
    assert store.claim_totp_counter("u1", 10) is False
    assert store.claim_totp_counter("u1", 11) is True

    store.save_session(SessionRecord(token_hash="s1", user_id="u1", expires_at=20))
    store.save_token(TokenRecord(
        token_hash="t1", user_id="u1", label="agent", expires_at=20,
    ))
    assert store.get_session("s1").user_id == "u1"
    assert store.get_token("t1").label == "agent"
    store.purge_expired(21)
    assert store.get_session("s1") is None
    assert store.get_token("t1") is None


def test_oidc_subjects_are_first_class_identities(store):
    store.save_user(user())
    store.save_oidc_identity("https://issuer.example", "subject-1", "u1")
    assert store.get_oidc_user_id("https://issuer.example", "subject-1") == "u1"
    assert store.get_oidc_user_id("https://other.example", "subject-1") is None


def test_challenges_are_shared_and_consumed_atomically(tmp_path):
    first = SqliteAuthStore(tmp_path / "auth.db")
    second = SqliteAuthStore(tmp_path / "auth.db")
    first.save_challenge(ChallengeRecord(
        token_hash="nonce", kind="oidc", payload="{}", expires_at=20,
    ))
    assert second.pop_challenge("nonce", "oidc", 10) is not None
    assert first.pop_challenge("nonce", "oidc", 10) is None


def test_rate_limits_are_shared_and_roll_windows(tmp_path):
    first = SqliteAuthStore(tmp_path / "auth.db")
    second = SqliteAuthStore(tmp_path / "auth.db")
    assert first.hit_rate_limit("login", limit=2, window_seconds=60, now=0)
    assert second.hit_rate_limit("login", limit=2, window_seconds=60, now=1)
    assert not first.hit_rate_limit("login", limit=2, window_seconds=60, now=2)
    assert second.hit_rate_limit("login", limit=2, window_seconds=60, now=61)


def test_duplicate_registration_is_a_database_decision(store):
    def save():
        try:
            store.save_user(user())
            return "saved"
        except DuplicateUserError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _index: save(), range(2))) == ["duplicate", "saved"]

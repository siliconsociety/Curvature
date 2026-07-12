"""Auth persistence: one narrow protocol, one hardened stdlib backend.

SQLite is the first-party baseline. Applications that need a remote store
implement this protocol explicitly; no half-hardened adapter ships as a promise.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class DuplicateUserError(Exception):
    pass


@dataclass(frozen=True)
class UserRecord:
    id: str
    email: str
    password_hash: str
    totp_secret: str | None = None
    last_totp_counter: int = -1


@dataclass(frozen=True)
class SessionRecord:
    token_hash: str
    user_id: str
    expires_at: float


@dataclass(frozen=True)
class TokenRecord:
    token_hash: str
    user_id: str
    label: str
    expires_at: float


@dataclass(frozen=True)
class ChallengeRecord:
    token_hash: str
    kind: str
    payload: str
    expires_at: float


class AuthStore(Protocol):
    def get_user_by_email(self, email: str) -> UserRecord | None: ...
    def get_user_by_id(self, user_id: str) -> UserRecord | None: ...
    def save_user(self, user: UserRecord) -> None: ...
    def get_session(self, token_hash: str) -> SessionRecord | None: ...
    def save_session(self, session: SessionRecord) -> None: ...
    def delete_session(self, token_hash: str) -> None: ...
    def get_token(self, token_hash: str) -> TokenRecord | None: ...
    def save_token(self, token: TokenRecord) -> None: ...
    def delete_token(self, token_hash: str, user_id: str) -> None: ...
    def list_tokens(self, user_id: str) -> list[TokenRecord]: ...
    def set_totp_secret(self, user_id: str, secret: str | None) -> None: ...
    def claim_totp_counter(self, user_id: str, counter: int) -> bool: ...
    def get_oidc_user_id(self, issuer: str, subject: str) -> str | None: ...
    def save_oidc_identity(self, issuer: str, subject: str, user_id: str) -> None: ...
    def save_challenge(self, challenge: ChallengeRecord) -> None: ...
    def pop_challenge(
        self, token_hash: str, kind: str, now: float
    ) -> ChallengeRecord | None: ...
    def hit_rate_limit(
        self, key: str, *, limit: int, window_seconds: int, now: float
    ) -> bool: ...
    def purge_expired(self, now: float) -> None: ...


def choose(data_dir: Path) -> AuthStore:
    from satellites.auth.store_sqlite import SqliteAuthStore

    return SqliteAuthStore(data_dir / "auth.db")

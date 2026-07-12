"""The revolving door (owner's ruling, 2026-07-11): narrow repositories,
never an ORM. This protocol is exactly as wide as Auth's needs and no
wider. Backends: sqlite (stdlib, default), jsonfile (toy scale). Mongo
arrives as its own satellite. Switch by editing one line in choose().
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class UserRecord:
    id: str
    email: str
    password_hash: str
    totp_secret: str | None = None


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


class AuthStore(Protocol):
    """Twelve verbs. If Auth ever needs a thirteenth, add it here and to
    every backend in the same commit — the protocol is the contract."""

    def get_user_by_email(self, email: str) -> UserRecord | None: ...
    def get_user_by_id(self, user_id: str) -> UserRecord | None: ...
    def save_user(self, user: UserRecord) -> None: ...
    def get_session(self, token_hash: str) -> SessionRecord | None: ...
    def save_session(self, session: SessionRecord) -> None: ...
    def delete_session(self, token_hash: str) -> None: ...
    def purge_expired(self, now: float) -> None: ...
    def get_token(self, token_hash: str) -> TokenRecord | None: ...
    def save_token(self, token: TokenRecord) -> None: ...
    def delete_token(self, token_hash: str, user_id: str) -> None: ...
    def list_tokens(self, user_id: str) -> list[TokenRecord]: ...
    def set_totp_secret(self, user_id: str, secret: str | None) -> None: ...


def choose(data_dir: Path) -> AuthStore:
    """The door revolves here: swap the returned backend, nothing else
    changes. Three doors ship: sqlite (stdlib, default), jsonfile (toy
    scale), and Mongo (a real server, on purpose — see store_mongo.py;
    `uv add pymongo`, hand the constructor a database object)."""
    from satellites.auth.store_sqlite import SqliteAuthStore

    return SqliteAuthStore(data_dir / "auth.db")

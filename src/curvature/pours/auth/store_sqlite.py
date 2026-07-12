"""SQLite backend — stdlib, single file, no server, real transactions.
The default door."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from satellites.auth.store import SessionRecord, TokenRecord, UserRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    totp_secret TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    label TEXT NOT NULL
);
"""


class SqliteAuthStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(path)
        with self._connect() as db:
            db.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self._path)
        db.row_factory = sqlite3.Row
        return db

    def get_user_by_email(self, email: str) -> UserRecord | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT id, email, password_hash, totp_secret FROM users WHERE email = ?", (email,)
            ).fetchone()
        return UserRecord(**row) if row else None

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT id, email, password_hash, totp_secret FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return UserRecord(**row) if row else None

    def save_user(self, user: UserRecord) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO users (id, email, password_hash, totp_secret) "
                "VALUES (?, ?, ?, ?)",
                (user.id, user.email, user.password_hash, user.totp_secret),
            )

    def set_totp_secret(self, user_id: str, secret: str | None) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE users SET totp_secret = ? WHERE id = ?", (secret, user_id)
            )

    def get_session(self, token_hash: str) -> SessionRecord | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT token_hash, user_id, expires_at FROM sessions WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
        return SessionRecord(**row) if row else None

    def save_session(self, session: SessionRecord) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (session.token_hash, session.user_id, session.expires_at),
            )

    def delete_session(self, token_hash: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def purge_expired(self, now: float) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))

    def get_token(self, token_hash: str) -> TokenRecord | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT token_hash, user_id, label FROM tokens WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
        return TokenRecord(**row) if row else None

    def save_token(self, token: TokenRecord) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO tokens (token_hash, user_id, label) VALUES (?, ?, ?)",
                (token.token_hash, token.user_id, token.label),
            )

    def delete_token(self, token_hash: str, user_id: str) -> None:
        with self._connect() as db:
            db.execute(
                "DELETE FROM tokens WHERE token_hash = ? AND user_id = ?",
                (token_hash, user_id),
            )

    def list_tokens(self, user_id: str) -> list[TokenRecord]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT token_hash, user_id, label FROM tokens WHERE user_id = ? "
                "ORDER BY label",
                (user_id,),
            ).fetchall()
        return [TokenRecord(**row) for row in rows]

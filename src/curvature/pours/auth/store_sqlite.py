"""SQLite Auth store: closed connections, WAL, bounded waits, atomic claims."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from satellites.auth.store import (
    ChallengeRecord,
    DuplicateUserError,
    SessionRecord,
    TokenRecord,
    UserRecord,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    totp_secret TEXT,
    last_totp_counter INTEGER NOT NULL DEFAULT -1
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS oidc_identities (
    issuer TEXT NOT NULL,
    subject TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (issuer, subject)
);
CREATE TABLE IF NOT EXISTS challenges (
    token_hash TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS rate_limits (
    key TEXT PRIMARY KEY,
    window_start REAL NOT NULL,
    attempts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS tokens_expiry ON tokens(expires_at);
CREATE INDEX IF NOT EXISTS challenges_expiry ON challenges(expires_at);
"""


class SqliteAuthStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(path)
        with self._db() as db:
            db.executescript(SCHEMA)
            self._migrate(db)

    @staticmethod
    def _migrate(db: sqlite3.Connection) -> None:
        user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
        if "last_totp_counter" not in user_columns:
            db.execute(
                "ALTER TABLE users ADD COLUMN last_totp_counter INTEGER NOT NULL DEFAULT -1"
            )
        token_columns = {row["name"] for row in db.execute("PRAGMA table_info(tokens)")}
        if "expires_at" not in token_columns:
            db.execute("ALTER TABLE tokens ADD COLUMN expires_at REAL NOT NULL DEFAULT 0")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self._path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 5000")
        db.execute("PRAGMA journal_mode = WAL")
        return db

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = self._connect()
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _user(row: sqlite3.Row | None) -> UserRecord | None:
        return UserRecord(**row) if row else None

    def get_user_by_email(self, email: str) -> UserRecord | None:
        with self._db() as db:
            row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return self._user(row)

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        with self._db() as db:
            row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._user(row)

    def save_user(self, user: UserRecord) -> None:
        try:
            with self._db() as db:
                db.execute(
                    "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                    (user.id, user.email, user.password_hash, user.totp_secret,
                     user.last_totp_counter),
                )
        except sqlite3.IntegrityError as error:
            raise DuplicateUserError(user.email) from error

    def set_totp_secret(self, user_id: str, secret: str | None) -> None:
        with self._db() as db:
            db.execute(
                "UPDATE users SET totp_secret = ?, last_totp_counter = -1 WHERE id = ?",
                (secret, user_id),
            )

    def claim_totp_counter(self, user_id: str, counter: int) -> bool:
        with self._db() as db:
            changed = db.execute(
                "UPDATE users SET last_totp_counter = ? "
                "WHERE id = ? AND last_totp_counter < ?",
                (counter, user_id, counter),
            ).rowcount
        return changed == 1

    def get_session(self, token_hash: str) -> SessionRecord | None:
        with self._db() as db:
            row = db.execute(
                "SELECT token_hash, user_id, expires_at FROM sessions WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
        return SessionRecord(**row) if row else None

    def save_session(self, session: SessionRecord) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO sessions VALUES (?, ?, ?)",
                (session.token_hash, session.user_id, session.expires_at),
            )

    def delete_session(self, token_hash: str) -> None:
        with self._db() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def get_token(self, token_hash: str) -> TokenRecord | None:
        with self._db() as db:
            row = db.execute("SELECT * FROM tokens WHERE token_hash = ?", (token_hash,)).fetchone()
        return TokenRecord(**row) if row else None

    def save_token(self, token: TokenRecord) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO tokens VALUES (?, ?, ?, ?)",
                (token.token_hash, token.user_id, token.label, token.expires_at),
            )

    def delete_token(self, token_hash: str, user_id: str) -> None:
        with self._db() as db:
            db.execute(
                "DELETE FROM tokens WHERE token_hash = ? AND user_id = ?",
                (token_hash, user_id),
            )

    def list_tokens(self, user_id: str) -> list[TokenRecord]:
        with self._db() as db:
            rows = db.execute(
                "SELECT * FROM tokens WHERE user_id = ? ORDER BY label", (user_id,)
            ).fetchall()
        return [TokenRecord(**row) for row in rows]

    def get_oidc_user_id(self, issuer: str, subject: str) -> str | None:
        with self._db() as db:
            row = db.execute(
                "SELECT user_id FROM oidc_identities WHERE issuer = ? AND subject = ?",
                (issuer, subject),
            ).fetchone()
        return str(row["user_id"]) if row else None

    def save_oidc_identity(self, issuer: str, subject: str, user_id: str) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO oidc_identities VALUES (?, ?, ?)",
                (issuer, subject, user_id),
            )

    def save_challenge(self, challenge: ChallengeRecord) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO challenges VALUES (?, ?, ?, ?)",
                (challenge.token_hash, challenge.kind, challenge.payload, challenge.expires_at),
            )

    def pop_challenge(
        self, token_hash: str, kind: str, now: float
    ) -> ChallengeRecord | None:
        with self._db() as db:
            row = db.execute(
                "DELETE FROM challenges WHERE token_hash = ? AND kind = ? AND expires_at >= ? "
                "RETURNING token_hash, kind, payload, expires_at",
                (token_hash, kind, now),
            ).fetchone()
        return ChallengeRecord(**row) if row else None

    def hit_rate_limit(
        self, key: str, *, limit: int, window_seconds: int, now: float
    ) -> bool:
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM rate_limits WHERE key = ?", (key,)).fetchone()
            if row is None or row["window_start"] + window_seconds <= now:
                db.execute(
                    "INSERT INTO rate_limits VALUES (?, ?, 1) "
                    "ON CONFLICT(key) DO UPDATE SET "
                    "window_start = excluded.window_start, attempts = 1",
                    (key, now),
                )
                return True
            if row["attempts"] >= limit:
                return False
            db.execute("UPDATE rate_limits SET attempts = attempts + 1 WHERE key = ?", (key,))
            return True

    def purge_expired(self, now: float) -> None:
        with self._db() as db:
            db.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
            db.execute("DELETE FROM tokens WHERE expires_at < ?", (now,))
            db.execute("DELETE FROM challenges WHERE expires_at < ?", (now,))
            db.execute("DELETE FROM rate_limits WHERE window_start < ?", (now - 86400,))

"""JSON-file backend — toy scale, single writer, whole-file rewrites.
Honest about what it is: fine below a thousand records and one process;
past that, the sqlite door is stdlib and one line away (store.choose)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from satellites.auth.store import SessionRecord, TokenRecord, UserRecord


class JsonAuthStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            self._write({"users": [], "sessions": [], "tokens": []})

    def _read(self) -> dict:
        return json.loads(self._path.read_text())

    def _write(self, data: dict) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self._path)

    def get_user_by_email(self, email: str) -> UserRecord | None:
        for user in self._read()["users"]:
            if user["email"] == email:
                return UserRecord(**user)
        return None

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        for user in self._read()["users"]:
            if user["id"] == user_id:
                return UserRecord(**user)
        return None

    def save_user(self, user: UserRecord) -> None:
        data = self._read()
        if any(u["email"] == user.email for u in data["users"]):
            raise ValueError(f"user {user.email!r} already exists")
        data["users"].append(asdict(user))
        self._write(data)

    def get_session(self, token_hash: str) -> SessionRecord | None:
        for session in self._read()["sessions"]:
            if session["token_hash"] == token_hash:
                return SessionRecord(**session)
        return None

    def save_session(self, session: SessionRecord) -> None:
        data = self._read()
        data["sessions"].append(asdict(session))
        self._write(data)

    def delete_session(self, token_hash: str) -> None:
        data = self._read()
        data["sessions"] = [s for s in data["sessions"] if s["token_hash"] != token_hash]
        self._write(data)

    def purge_expired(self, now: float) -> None:
        data = self._read()
        data["sessions"] = [s for s in data["sessions"] if s["expires_at"] >= now]
        self._write(data)

    def get_token(self, token_hash: str) -> TokenRecord | None:
        for token in self._read().get("tokens", []):
            if token["token_hash"] == token_hash:
                return TokenRecord(**token)
        return None

    def save_token(self, token: TokenRecord) -> None:
        data = self._read()
        data.setdefault("tokens", []).append(asdict(token))
        self._write(data)

    def delete_token(self, token_hash: str, user_id: str) -> None:
        data = self._read()
        data["tokens"] = [
            t for t in data.get("tokens", [])
            if not (t["token_hash"] == token_hash and t["user_id"] == user_id)
        ]
        self._write(data)

    def set_totp_secret(self, user_id: str, secret: str | None) -> None:
        data = self._read()
        for user in data["users"]:
            if user["id"] == user_id:
                user["totp_secret"] = secret
        self._write(data)

    def list_tokens(self, user_id: str) -> list[TokenRecord]:
        return sorted(
            (TokenRecord(**t) for t in self._read().get("tokens", [])
             if t["user_id"] == user_id),
            key=lambda token: token.label,
        )

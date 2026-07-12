"""Mongo backend — a real server, on purpose, first-class, never the
default. The third door on the revolving door.

Wire it in choose() or app assembly:

    from pymongo import MongoClient
    from satellites.auth.store_mongo import MongoAuthStore

    store = MongoAuthStore(MongoClient(uri)["myapp"])
    store.ensure_indexes()

Requires pymongo (`uv add pymongo`). The constructor takes a database
object, not a URI — the seam that keeps tests hermetic: hand it a fake
with the same five collection verbs and no server ever runs.
"""

from __future__ import annotations

from typing import Any

from satellites.auth.store import SessionRecord, TokenRecord, UserRecord


class MongoAuthStore:
    def __init__(self, database: Any) -> None:
        self._users = database["auth_users"]
        self._sessions = database["auth_sessions"]
        self._tokens = database["auth_tokens"]

    def ensure_indexes(self) -> None:
        self._users.create_index("email", unique=True)
        self._sessions.create_index("token_hash", unique=True)
        self._tokens.create_index("token_hash", unique=True)

    @staticmethod
    def _user(document: dict | None) -> UserRecord | None:
        if document is None:
            return None
        return UserRecord(
            id=document["id"],
            email=document["email"],
            password_hash=document["password_hash"],
            totp_secret=document.get("totp_secret"),
        )

    def get_user_by_email(self, email: str) -> UserRecord | None:
        return self._user(self._users.find_one({"email": email}))

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        return self._user(self._users.find_one({"id": user_id}))

    def save_user(self, user: UserRecord) -> None:
        self._users.insert_one({
            "id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "totp_secret": user.totp_secret,
        })

    def set_totp_secret(self, user_id: str, secret: str | None) -> None:
        self._users.update_one({"id": user_id}, {"$set": {"totp_secret": secret}})

    def get_session(self, token_hash: str) -> SessionRecord | None:
        document = self._sessions.find_one({"token_hash": token_hash})
        if document is None:
            return None
        return SessionRecord(
            token_hash=document["token_hash"],
            user_id=document["user_id"],
            expires_at=document["expires_at"],
        )

    def save_session(self, session: SessionRecord) -> None:
        self._sessions.insert_one({
            "token_hash": session.token_hash,
            "user_id": session.user_id,
            "expires_at": session.expires_at,
        })

    def delete_session(self, token_hash: str) -> None:
        self._sessions.delete_one({"token_hash": token_hash})

    def purge_expired(self, now: float) -> None:
        self._sessions.delete_many({"expires_at": {"$lt": now}})

    def get_token(self, token_hash: str) -> TokenRecord | None:
        document = self._tokens.find_one({"token_hash": token_hash})
        if document is None:
            return None
        return TokenRecord(
            token_hash=document["token_hash"],
            user_id=document["user_id"],
            label=document["label"],
        )

    def save_token(self, token: TokenRecord) -> None:
        self._tokens.insert_one({
            "token_hash": token.token_hash,
            "user_id": token.user_id,
            "label": token.label,
        })

    def delete_token(self, token_hash: str, user_id: str) -> None:
        self._tokens.delete_one({"token_hash": token_hash, "user_id": user_id})

    def list_tokens(self, user_id: str) -> list[TokenRecord]:
        documents = sorted(
            self._tokens.find({"user_id": user_id}), key=lambda d: d["label"]
        )
        return [
            TokenRecord(token_hash=d["token_hash"], user_id=d["user_id"], label=d["label"])
            for d in documents
        ]

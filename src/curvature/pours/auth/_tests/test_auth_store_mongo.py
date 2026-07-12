"""Poured with the Auth satellite: the Mongo door, proven against an
in-repo fake — hermetic by religion, no server ever runs. The fake
speaks the five collection verbs the adapter uses and nothing more."""

import pytest
from satellites.auth.store import SessionRecord, TokenRecord, UserRecord
from satellites.auth.store_mongo import MongoAuthStore


class FakeCollection:
    def __init__(self):
        self.documents = []
        self.indexes = []

    def create_index(self, key, unique=False):
        self.indexes.append((key, unique))

    @staticmethod
    def _matches(document, query):
        for field, condition in query.items():
            if isinstance(condition, dict) and "$lt" in condition:
                if not document.get(field) < condition["$lt"]:
                    return False
            elif document.get(field) != condition:
                return False
        return True

    def find_one(self, query):
        return next((d for d in self.documents if self._matches(d, query)), None)

    def find(self, query):
        return [d for d in self.documents if self._matches(d, query)]

    def insert_one(self, document):
        self.documents.append(dict(document))

    def update_one(self, query, update):
        target = self.find_one(query)
        if target is not None:
            target.update(update["$set"])

    def delete_one(self, query):
        target = self.find_one(query)
        if target is not None:
            self.documents.remove(target)

    def delete_many(self, query):
        self.documents = [d for d in self.documents if not self._matches(d, query)]


class FakeDatabase(dict):
    def __missing__(self, name):
        self[name] = FakeCollection()
        return self[name]


@pytest.fixture
def store():
    store = MongoAuthStore(FakeDatabase())
    store.ensure_indexes()
    return store


def test_indexes_are_declared_unique(store):
    assert ("email", True) in store._users.indexes


def test_user_round_trip_including_totp(store):
    user = UserRecord(id="u1", email="pit@crew.example", password_hash="scrypt$x$y")
    store.save_user(user)
    assert store.get_user_by_email("pit@crew.example").id == "u1"
    assert store.get_user_by_id("u1").totp_secret is None
    store.set_totp_secret("u1", "BASE32SECRET")
    assert store.get_user_by_id("u1").totp_secret == "BASE32SECRET"
    store.set_totp_secret("u1", None)
    assert store.get_user_by_id("u1").totp_secret is None


def test_missing_users_are_none(store):
    assert store.get_user_by_email("ghost@example.com") is None
    assert store.get_user_by_id("ghost") is None


def test_session_lifecycle(store):
    store.save_session(SessionRecord(token_hash="h1", user_id="u1", expires_at=100.0))
    store.save_session(SessionRecord(token_hash="h2", user_id="u1", expires_at=900.0))
    assert store.get_session("h1").user_id == "u1"
    store.purge_expired(now=500.0)
    assert store.get_session("h1") is None      # expired: purged
    assert store.get_session("h2") is not None  # still alive
    store.delete_session("h2")
    assert store.get_session("h2") is None


def test_token_lifecycle_scoped_to_the_owner(store):
    store.save_token(TokenRecord(token_hash="t1", user_id="u1", label="laptop"))
    store.save_token(TokenRecord(token_hash="t2", user_id="u1", label="agent"))
    store.save_token(TokenRecord(token_hash="t3", user_id="u2", label="other"))
    assert [t.label for t in store.list_tokens("u1")] == ["agent", "laptop"]
    store.delete_token("t1", user_id="u2")      # wrong owner: nothing happens
    assert store.get_token("t1") is not None
    store.delete_token("t1", user_id="u1")
    assert store.get_token("t1") is None

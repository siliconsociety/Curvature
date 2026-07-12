"""Assembled standards, invented nothing: scrypt from the standard
library for passwords, secrets for tokens, sha256 for token storage
(sessions are random, not guessable — hashing them means a leaked store
still leaks no usable cookies), hmac.compare_digest against timing."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time as _time
import urllib.parse

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 5
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P
    )
    return f"scrypt$n={SCRYPT_N},r={SCRYPT_R},p={SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        parts = stored.split("$")
        if len(parts) == 3:  # 0.2 compatibility; rehash after successful login
            scheme, salt_hex, digest_hex = parts
            n, r, p = SCRYPT_N, SCRYPT_R, SCRYPT_P
        else:
            scheme, parameters, salt_hex, digest_hex = parts
            parsed = dict(part.split("=", 1) for part in parameters.split(","))
            n, r, p = int(parsed["n"]), int(parsed["r"]), int(parsed["p"])
        if scheme != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (KeyError, ValueError):
        return False
    candidate = hashlib.scrypt(
        password.encode(), salt=salt, n=n, r=r, p=p
    )
    return hmac.compare_digest(candidate, expected)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# --- TOTP (RFC 6238) — assembled from the standard library ------------------

TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode()


def totp_counter(at: float | None = None) -> int:
    return int((at if at is not None else _time.time()) // TOTP_STEP_SECONDS)


def totp_code(secret: str, at: float | None = None) -> str:
    key = base64.b32decode(secret)
    counter = totp_counter(at)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(number % (10 ** TOTP_DIGITS)).zfill(TOTP_DIGITS)


def match_totp_counter(secret: str, code: str, at: float | None = None) -> int | None:
    """Return the matching counter so the store can reject replay atomically."""
    now = at if at is not None else _time.time()
    try:
        for drift in (-1, 0, 1):
            candidate_at = now + drift * TOTP_STEP_SECONDS
            if hmac.compare_digest(totp_code(secret, candidate_at), code.strip()):
                return totp_counter(candidate_at)
    except (ValueError, TypeError):
        return None
    return None


def verify_totp(secret: str, code: str, at: float | None = None) -> bool:
    return match_totp_counter(secret, code, at) is not None


def otpauth_uri(secret: str, email: str, app_name: str) -> str:
    label = urllib.parse.quote(f"{app_name}:{email}", safe="")
    query = urllib.parse.urlencode({"secret": secret, "issuer": app_name})
    return f"otpauth://totp/{label}?{query}"

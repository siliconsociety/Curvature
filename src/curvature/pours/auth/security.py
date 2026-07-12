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

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 5
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P
    )
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _scheme, salt_hex, digest_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    candidate = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P
    )
    return hmac.compare_digest(candidate.hex(), digest_hex)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# --- TOTP (RFC 6238) — assembled from the standard library ------------------

TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode()


def totp_code(secret: str, at: float | None = None) -> str:
    key = base64.b32decode(secret)
    counter = int((at if at is not None else _time.time()) // TOTP_STEP_SECONDS)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(number % (10 ** TOTP_DIGITS)).zfill(TOTP_DIGITS)


def verify_totp(secret: str, code: str, at: float | None = None) -> bool:
    """Accept the neighboring windows: clocks drift, humans type slowly."""
    now = at if at is not None else _time.time()
    return any(
        hmac.compare_digest(totp_code(secret, now + drift * TOTP_STEP_SECONDS), code.strip())
        for drift in (-1, 0, 1)
    )


def otpauth_uri(secret: str, email: str, app_name: str) -> str:
    return f"otpauth://totp/{app_name}:{email}?secret={secret}&issuer={app_name}"

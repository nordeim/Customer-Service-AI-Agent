from __future__ import annotations

import base64
import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext

from .exceptions import AuthenticationError, SecurityError, ValidationError
from .config import get_settings


_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValidationError("Password does not meet minimum length requirements")
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def _jwt_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_jwt_token(subject: str, *, scopes: Optional[list[str]] = None, ttl_seconds: Optional[int] = None, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    settings = get_settings()
    sec = settings.security
    ttl = ttl_seconds or sec.jwt.access_ttl_seconds

    now = _jwt_now()
    payload: Dict[str, Any] = {
        "sub": subject,
        "iss": sec.jwt.issuer,
        "aud": sec.jwt.audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    if scopes:
        payload["scopes"] = scopes
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, sec.secret_key, algorithm=sec.jwt.algorithm)


def verify_jwt_token(token: str, *, require_aud: bool = True) -> Dict[str, Any]:
    settings = get_settings()
    sec = settings.security
    options = {"require": ["exp", "iat", "iss"]}
    try:
        decoded = jwt.decode(
            token,
            sec.secret_key,
            algorithms=[sec.jwt.algorithm],
            audience=sec.jwt.audience if require_aud else None,
            issuer=sec.jwt.issuer,
            options=options,
        )
        return decoded
    except jwt.PyJWTError as e:
        raise AuthenticationError(f"Invalid token: {e}")


def hmac_sign(message: bytes, *, secret: Optional[bytes] = None) -> str:
    settings = get_settings()
    key = secret or settings.security.hmac_secret.encode()
    signature = hmac.new(key, message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).decode()


def hmac_verify(message: bytes, signature_b64: str, *, secret: Optional[bytes] = None) -> bool:
    expected = hmac_sign(message, secret=secret)
    try:
        return hmac.compare_digest(expected, signature_b64)
    except Exception:
        return False


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.security.encryption_key
    # Accept raw 32-byte base64 key or plain. If plain, base64-url encode to 32 bytes.
    try:
        # If already base64 32-byte, Fernet will accept
        base64.urlsafe_b64decode(key)
        fkey = key.encode()
    except Exception:
        # Derive 32-byte key from provided string
        derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        fkey = derived
    return Fernet(fkey)


def encrypt_field(value: str) -> str:
    try:
        f = _get_fernet()
        token = f.encrypt(value.encode())
        return token.decode()
    except Exception as e:
        raise SecurityError(f"Encryption failed: {e}")


def decrypt_field(token: str) -> str:
    try:
        f = _get_fernet()
        value = f.decrypt(token.encode())
        return value.decode()
    except InvalidToken as e:
        raise SecurityError(f"Decryption failed: invalid token: {e}")
    except Exception as e:
        raise SecurityError(f"Decryption failed: {e}")

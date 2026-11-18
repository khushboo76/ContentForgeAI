"""
Cryptographic security module:
- Fernet AES-128-CBC + HMAC symmetric encryption for OAuth tokens at rest.
- Cryptographic state token generation & verification for OAuth CSRF protection.
"""
import base64
import hashlib
import json
import time
from cryptography.fernet import Fernet
from app.core import config

_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        raw_key = config.TOKEN_ENCRYPTION_KEY.strip()
        if not raw_key:
            # Derive a deterministic 32-byte urlsafe base64 key from SECRET_KEY
            derived = hashlib.sha256(config.SECRET_KEY.encode()).digest()
            raw_key = base64.urlsafe_b64encode(derived).decode()
        _fernet_instance = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)
    return _fernet_instance


def encrypt_token(raw_token: str) -> str:
    """Encrypts an OAuth access or refresh token before database storage."""
    if not raw_token:
        return ""
    f = _get_fernet()
    return f.encrypt(raw_token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypts an OAuth token for in-memory API usage."""
    if not encrypted_token:
        return ""
    f = _get_fernet()
    return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")


def create_oauth_state(user_id: str, platform: str) -> str:
    """
    Creates an encrypted, tamper-proof state token containing user context.
    Valid for 15 minutes.
    """
    payload = {
        "uid": user_id,
        "plt": platform,
        "ts": int(time.time()),
    }
    f = _get_fernet()
    raw_json = json.dumps(payload).encode("utf-8")
    return f.encrypt(raw_json).decode("utf-8")


def verify_oauth_state(state_token: str, max_age_seconds: int = 900) -> dict:
    """
    Decrypts and validates the state token.
    Raises ValueError if invalid, tampered with, or expired.
    """
    f = _get_fernet()
    try:
        decrypted_bytes = f.decrypt(state_token.encode("utf-8"), ttl=max_age_seconds)
        data = json.loads(decrypted_bytes.decode("utf-8"))
        return {
            "user_id": data["uid"],
            "platform": data["plt"],
            "created_at": data["ts"],
        }
    except Exception as exc:
        raise ValueError(f"Invalid or expired OAuth state parameter: {exc}") from exc

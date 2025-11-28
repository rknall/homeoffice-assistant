"""Encryption utilities using Fernet symmetric encryption."""
import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet

from src.config import settings


def get_fernet() -> Fernet:
    """Get Fernet instance using derived key from SECRET_KEY."""
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.secret_key.encode()).digest()
    )
    return Fernet(key)


def encrypt_config(config: dict[str, Any]) -> str:
    """Encrypt a configuration dictionary to a string."""
    return get_fernet().encrypt(json.dumps(config).encode()).decode()


def decrypt_config(encrypted: str) -> dict[str, Any]:
    """Decrypt a configuration string to a dictionary."""
    return json.loads(get_fernet().decrypt(encrypted.encode()).decode())


def encrypt_value(value: str) -> str:
    """Encrypt a single string value."""
    return get_fernet().encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """Decrypt a single string value."""
    return get_fernet().decrypt(encrypted.encode()).decode()

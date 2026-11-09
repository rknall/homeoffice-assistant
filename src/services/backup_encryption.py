# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Password-based encryption utilities for backup files."""

import base64
import logging
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# OWASP 2023 recommendation for PBKDF2-SHA256
PBKDF2_ITERATIONS = 480_000
SALT_LENGTH = 16


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a password using PBKDF2.

    Args:
        password: User-provided password
        salt: Random salt (16 bytes)

    Returns:
        32-byte key suitable for Fernet encryption
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_backup_archive(tarball_bytes: bytes, password: str) -> tuple[bytes, bytes]:
    """Encrypt a backup archive with a password.

    Args:
        tarball_bytes: The raw tar.gz backup data
        password: User-provided password

    Returns:
        Tuple of (encrypted_bytes, salt)
    """
    salt = os.urandom(SALT_LENGTH)
    key = derive_key_from_password(password, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(tarball_bytes)
    return encrypted, salt


def decrypt_backup_archive(encrypted_bytes: bytes, password: str, salt: bytes) -> bytes:
    """Decrypt a password-protected backup archive.

    Args:
        encrypted_bytes: The encrypted backup data
        password: User-provided password
        salt: Salt used during encryption

    Returns:
        Decrypted tar.gz bytes

    Raises:
        InvalidToken: If password is incorrect or data is corrupted
    """
    key = derive_key_from_password(password, salt)
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_bytes)


class BackupDecryptionError(Exception):
    """Raised when backup decryption fails."""

    pass


def try_decrypt_backup(
    encrypted_bytes: bytes, password: str, salt: bytes
) -> tuple[bool, bytes | None, str]:
    """Attempt to decrypt a backup with error handling.

    Args:
        encrypted_bytes: The encrypted backup data
        password: User-provided password
        salt: Salt used during encryption

    Returns:
        Tuple of (success, decrypted_bytes, error_message)
    """
    try:
        decrypted = decrypt_backup_archive(encrypted_bytes, password, salt)
        return True, decrypted, ""
    except InvalidToken:
        return False, None, "Invalid password or corrupted backup"
    except Exception:
        logger.exception("Backup decryption failed")
        return False, None, "Decryption error, see server log"

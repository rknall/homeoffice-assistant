# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
import os

import pytest
from cryptography.fernet import InvalidToken

# Set test environment
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars!"  # noqa: S105

from src.encryption import decrypt_config, encrypt_config


class TestEncryption:
    """Test encryption utilities."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption work correctly."""
        original_config = {
            "url": "https://paperless.example.com",
            "token": "secret-api-token-12345",
            "custom_field_name": "Trip",
        }

        encrypted = encrypt_config(original_config)

        assert encrypted != str(original_config)
        assert "secret-api-token" not in encrypted

        decrypted = decrypt_config(encrypted)

        assert decrypted == original_config

    def test_encrypt_produces_different_output(self):
        """Test that encryption produces different ciphertext each time (due to IV)."""
        config = {"key": "value"}

        encrypted1 = encrypt_config(config)
        encrypted2 = encrypt_config(config)

        # Fernet includes timestamp and IV, so outputs should differ
        # But both should decrypt to the same value
        assert decrypt_config(encrypted1) == decrypt_config(encrypted2) == config

    def test_encrypt_empty_config(self):
        """Test encrypting an empty config."""
        config = {}

        encrypted = encrypt_config(config)
        decrypted = decrypt_config(encrypted)

        assert decrypted == {}

    def test_encrypt_complex_config(self):
        """Test encrypting a complex nested config."""
        config = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {
                "key": "value",
            },
        }

        encrypted = encrypt_config(config)
        decrypted = decrypt_config(encrypted)

        assert decrypted == config

    def test_decrypt_invalid_data_raises(self):
        """Test that decrypting invalid data raises an error."""
        with pytest.raises((InvalidToken, ValueError)):
            decrypt_config("not-valid-encrypted-data")

    def test_decrypt_tampered_data_raises(self):
        """Test that decrypting tampered data raises an error."""
        config = {"key": "value"}
        encrypted = encrypt_config(config)
        # Tamper with the encrypted data
        tampered = encrypted[:-5] + "XXXXX"

        with pytest.raises((InvalidToken, ValueError)):
            decrypt_config(tampered)

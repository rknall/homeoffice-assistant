# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Masking and merging of secret values in JSON-schema described configs.

A field is secret when its schema property declares ``format: "password"``.
The same schema drives the edit form, so the form and the masking can never
disagree about which fields hold credentials.
"""

from typing import Any

# Masked secrets are sent as an empty string; the edit form shows a blank
# field and sends it back blank when the user keeps the stored value.
MASK = ""


def secret_fields(schema: dict[str, Any]) -> set[str]:
    """Return the names of the secret fields in a config schema.

    Args:
        schema: JSON schema with a ``properties`` mapping.

    Returns:
        The property names whose ``format`` is ``"password"``.
    """
    properties = schema.get("properties") or {}
    return {
        name
        for name, spec in properties.items()
        if isinstance(spec, dict) and spec.get("format") == "password"
    }


def mask(config: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a config with every set secret replaced by the mask.

    Args:
        config: Decrypted configuration values.
        schema: JSON schema describing the configuration.

    Returns:
        A new dict in which every non-empty secret value is ``MASK``.
    """
    masked = dict(config)
    for name in secret_fields(schema):
        if masked.get(name):
            masked[name] = MASK
    return masked


def merge(
    stored: dict[str, Any], incoming: dict[str, Any], schema: dict[str, Any]
) -> dict[str, Any]:
    """Combine incoming values with the stored secrets they leave blank.

    A secret that is missing or empty in ``incoming`` (the masked value sent
    back by the edit form) keeps its stored value. Every other field is taken
    from ``incoming`` as is.

    Args:
        stored: Currently stored, decrypted configuration.
        incoming: Configuration values submitted by the client.
        schema: JSON schema describing the configuration.

    Returns:
        A new dict with the merged configuration.
    """
    merged = dict(incoming)
    for name in secret_fields(schema):
        if not merged.get(name) and stored.get(name):
            merged[name] = stored[name]
    return merged


def set_secret_fields(config: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Return the names of the secret fields that hold a value.

    The mask is blank, so a client cannot tell a stored secret from none;
    this list carries that fact without any secret value.

    Args:
        config: Decrypted configuration values.
        schema: JSON schema describing the configuration.

    Returns:
        Sorted names of secret fields with a non-empty value.
    """
    return sorted(name for name in secret_fields(schema) if config.get(name))

# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for plugin permissions system."""

import pytest

from src.plugins.base import Permission
from src.plugins.permissions import (
    DANGEROUS_PERMISSIONS,
    SAFE_PERMISSIONS,
    PermissionChecker,
)


class TestPermissionConstants:
    """Tests for permission constant sets."""

    def test_dangerous_permissions_contains_write_all(self):
        """Test that dangerous permissions includes write-all permissions."""
        assert Permission.USER_WRITE_ALL in DANGEROUS_PERMISSIONS
        assert Permission.SYSTEM_SETTINGS_WRITE in DANGEROUS_PERMISSIONS

    def test_safe_permissions_contains_read_only(self):
        """Test that safe permissions includes read-only permissions."""
        assert Permission.USER_READ in SAFE_PERMISSIONS
        assert Permission.EVENT_READ in SAFE_PERMISSIONS
        assert Permission.COMPANY_READ in SAFE_PERMISSIONS
        assert Permission.EXPENSE_READ in SAFE_PERMISSIONS

    def test_no_overlap_between_dangerous_and_safe(self):
        """Test that dangerous and safe permissions don't overlap."""
        overlap = DANGEROUS_PERMISSIONS & SAFE_PERMISSIONS
        assert len(overlap) == 0, f"Overlapping permissions: {overlap}"


class TestPermissionChecker:
    """Tests for PermissionChecker class."""

    @pytest.fixture
    def checker(self):
        """Create a PermissionChecker instance."""
        return PermissionChecker()

    def test_parse_valid_permissions(self, checker):
        """Test parsing valid permission strings."""
        valid, invalid = checker.parse_permissions([
            "user.read",
            "event.write",
            "company.read",
        ])
        assert Permission.USER_READ in valid
        assert Permission.EVENT_WRITE in valid
        assert Permission.COMPANY_READ in valid
        assert len(invalid) == 0

    def test_parse_invalid_permissions(self, checker):
        """Test parsing invalid permission strings."""
        valid, invalid = checker.parse_permissions([
            "user.read",
            "invalid.permission",
            "another.invalid",
        ])
        assert Permission.USER_READ in valid
        assert len(valid) == 1
        assert "invalid.permission" in invalid
        assert "another.invalid" in invalid

    def test_parse_empty_list(self, checker):
        """Test parsing empty permission list."""
        valid, invalid = checker.parse_permissions([])
        assert len(valid) == 0
        assert len(invalid) == 0

    def test_parse_all_invalid(self, checker):
        """Test parsing list with all invalid permissions."""
        valid, invalid = checker.parse_permissions([
            "not.a.permission",
            "fake.perm",
        ])
        assert len(valid) == 0
        assert len(invalid) == 2

    def test_get_dangerous_permissions(self, checker):
        """Test identifying dangerous permissions."""
        permissions = {
            Permission.USER_READ,
            Permission.USER_WRITE_ALL,
            Permission.SYSTEM_SETTINGS_WRITE,
        }
        dangerous = checker.get_dangerous_permissions(permissions)
        assert Permission.USER_WRITE_ALL in dangerous
        assert Permission.SYSTEM_SETTINGS_WRITE in dangerous
        assert Permission.USER_READ not in dangerous

    def test_get_dangerous_permissions_none(self, checker):
        """Test when no dangerous permissions present."""
        permissions = {
            Permission.USER_READ,
            Permission.EVENT_READ,
        }
        dangerous = checker.get_dangerous_permissions(permissions)
        assert len(dangerous) == 0

    def test_get_safe_permissions(self, checker):
        """Test getting safe permissions from a set."""
        permissions = {
            Permission.USER_READ,
            Permission.USER_WRITE_ALL,
            Permission.EVENT_READ,
        }
        safe = checker.get_safe_permissions(permissions)
        assert Permission.USER_READ in safe
        assert Permission.EVENT_READ in safe
        assert Permission.USER_WRITE_ALL not in safe

    def test_is_permission_valid(self, checker):
        """Test checking if permission string is valid."""
        assert checker.is_permission_valid("user.read") is True
        assert checker.is_permission_valid("event.write") is True
        assert checker.is_permission_valid("invalid.permission") is False
        assert checker.is_permission_valid("not.a.perm") is False

    def test_check_permissions_subset_all_granted(self, checker):
        """Test checking permissions subset when all granted."""
        required = {Permission.USER_READ, Permission.EVENT_READ}
        granted = {Permission.USER_READ, Permission.EVENT_READ, Permission.EXPENSE_READ}

        all_granted, missing = checker.check_permissions_subset(required, granted)

        assert all_granted is True
        assert len(missing) == 0

    def test_check_permissions_subset_missing(self, checker):
        """Test checking permissions subset with missing permissions."""
        required = {
            Permission.USER_READ, Permission.EVENT_WRITE, Permission.EXPENSE_WRITE
        }
        granted = {Permission.USER_READ}

        all_granted, missing = checker.check_permissions_subset(required, granted)

        assert all_granted is False
        assert Permission.EVENT_WRITE in missing
        assert Permission.EXPENSE_WRITE in missing
        assert Permission.USER_READ not in missing

    def test_format_permissions_for_display(self, checker):
        """Test formatting permissions for UI display."""
        permissions = {Permission.USER_READ, Permission.USER_WRITE_ALL}

        formatted = checker.format_permissions_for_display(permissions)

        assert len(formatted) == 2
        # Check that dangerous permissions are flagged
        dangerous_entry = next(
            (p for p in formatted if p["value"] == "user.write.all"), None
        )
        assert dangerous_entry is not None
        assert dangerous_entry["dangerous"] is True

        safe_entry = next(
            (p for p in formatted if p["value"] == "user.read"), None
        )
        assert safe_entry is not None
        assert safe_entry["dangerous"] is False

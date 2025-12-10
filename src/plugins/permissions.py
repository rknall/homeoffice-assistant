# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Permission checking for the plugin system."""

from src.plugins.base import Permission

# Permissions that require admin approval or special handling
DANGEROUS_PERMISSIONS: set[Permission] = {
    Permission.USER_WRITE_ALL,
    Permission.INTEGRATION_CONFIG,
    Permission.SYSTEM_SETTINGS_WRITE,
}

# Permissions that are safe for most plugins
SAFE_PERMISSIONS: set[Permission] = {
    Permission.USER_READ,
    Permission.USER_WRITE_SELF,
    Permission.EVENT_READ,
    Permission.COMPANY_READ,
    Permission.EXPENSE_READ,
    Permission.CALENDAR_READ,
    Permission.INTEGRATION_USE,
    Permission.SYSTEM_SETTINGS_READ,
}


class PermissionChecker:
    """Validates and checks plugin permissions."""

    def get_dangerous_permissions(
        self,
        permissions: set[Permission],
    ) -> set[Permission]:
        """Get the subset of permissions that are considered dangerous.

        Args:
            permissions: Set of permissions to check

        Returns:
            Set of dangerous permissions from the input
        """
        return permissions & DANGEROUS_PERMISSIONS

    def get_safe_permissions(
        self,
        permissions: set[Permission],
    ) -> set[Permission]:
        """Get the subset of permissions that are considered safe.

        Args:
            permissions: Set of permissions to check

        Returns:
            Set of safe permissions from the input
        """
        return permissions & SAFE_PERMISSIONS

    def is_permission_valid(self, permission_str: str) -> bool:
        """Check if a permission string is a valid Permission enum value.

        Args:
            permission_str: Permission string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            Permission(permission_str)
            return True
        except ValueError:
            return False

    def parse_permissions(
        self,
        permission_strings: list[str],
    ) -> tuple[set[Permission], list[str]]:
        """Parse a list of permission strings into Permission enums.

        Args:
            permission_strings: List of permission strings

        Returns:
            Tuple of (valid permissions set, list of invalid permission strings)
        """
        valid: set[Permission] = set()
        invalid: list[str] = []

        for perm_str in permission_strings:
            try:
                valid.add(Permission(perm_str))
            except ValueError:
                invalid.append(perm_str)

        return valid, invalid

    def check_permissions_subset(
        self,
        required: set[Permission],
        granted: set[Permission],
    ) -> tuple[bool, set[Permission]]:
        """Check if all required permissions are in the granted set.

        Args:
            required: Set of required permissions
            granted: Set of granted permissions

        Returns:
            Tuple of (all_granted, missing_permissions)
        """
        missing = required - granted
        return len(missing) == 0, missing

    def format_permissions_for_display(
        self,
        permissions: set[Permission],
    ) -> list[dict[str, str]]:
        """Format permissions for UI display.

        Args:
            permissions: Set of permissions

        Returns:
            List of dicts with 'value', 'label', and 'dangerous' keys
        """
        result = []
        for perm in sorted(permissions, key=lambda p: p.value):
            result.append({
                "value": perm.value,
                "label": perm.value.replace(".", " ").replace("_", " ").title(),
                "dangerous": perm in DANGEROUS_PERMISSIONS,
            })
        return result

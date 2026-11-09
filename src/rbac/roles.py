# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Default roles seeded on first run and the role names the code relies on."""

from .permissions import CORE_PERMISSIONS

# Name of the system role that holds every permission.
GLOBAL_ADMIN_ROLE = "Global Admin"

# Name of the default role for regular users. It grants what a user without
# any role could do before company-scoped checks existed.
MEMBER_ROLE = "Member"

# Global Admin always gets all core permissions
GLOBAL_ADMIN_PERMISSIONS = [p["code"] for p in CORE_PERMISSIONS]

# Core permissions of the Member role. Plugin permissions flagged
# ``member_default`` in a manifest are added when the plugin registers them.
MEMBER_PERMISSIONS = [
    "user.read",
    "user.write.self",
    "company.view",
    "company.manage",
    "event.read",
    "event.write",
    "event.delete",
    "expense.view",
    "expense.manage",
    "integration.use",
    "system.settings.read",
]

# Default roles to seed on first run
# Only Global Admin is a true system role (is_system=True) and cannot be modified
# Other roles are seeded as regular roles and can be fully managed via UI
DEFAULT_ROLES = [
    {
        "name": GLOBAL_ADMIN_ROLE,
        "is_system": True,
        "description": "Grants all permissions across the entire system.",
        "permissions": GLOBAL_ADMIN_PERMISSIONS,
    },
    {
        "name": MEMBER_ROLE,
        "is_system": False,
        "description": "Default role for regular users: own events, expenses "
        "and companies.",
        "permissions": MEMBER_PERMISSIONS,
    },
    {
        "name": "Company Admin",
        "is_system": False,
        "description": "Grants administrative permissions for an assigned company.",
        "permissions": [
            "company.view",
            "company.manage",
            "expense.view",
            "expense.manage",
            "event.read",
            "event.write",
            "event.delete",
        ],
    },
    {
        "name": "Company Viewer",
        "is_system": False,
        "description": "Grants read-only permissions for an assigned company.",
        "permissions": [
            "company.view",
            "expense.view",
            "event.read",
        ],
    },
]

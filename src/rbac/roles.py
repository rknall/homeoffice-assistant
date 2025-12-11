# src/rbac/roles.py
from .permissions import CORE_PERMISSIONS

# Global Admin always gets all core permissions
GLOBAL_ADMIN_PERMISSIONS = [p["code"] for p in CORE_PERMISSIONS]

# Default roles to seed on first run
# Only Global Admin is a true system role (is_system=True) and cannot be modified
# Other roles are seeded as regular roles and can be fully managed via UI
DEFAULT_ROLES = [
    {
        "name": "Global Admin",
        "is_system": True,
        "description": "Grants all permissions across the entire system.",
        "permissions": GLOBAL_ADMIN_PERMISSIONS,
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

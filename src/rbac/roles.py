# src/rbac/roles.py
from .permissions import CORE_PERMISSIONS

GLOBAL_ADMIN_PERMISSIONS = [p["code"] for p in CORE_PERMISSIONS]
COMPANY_ADMIN_PERMISSIONS = [
    "company.view",
    "company.manage",
    "expense.view",
    "expense.manage",
    "notes.view",
    "notes.edit",
    "event.read",
    "event.write",
    "event.delete",
]
COMPANY_VIEWER_PERMISSIONS = [
    "company.view",
    "expense.view",
    "notes.view",
    "event.read",
]

DEFAULT_ROLES = [
    {
        "name": "Global Admin",
        "is_system": True,
        "description": "Grants all permissions across the entire system.",
        "permissions": GLOBAL_ADMIN_PERMISSIONS,
    },
    {
        "name": "Company Admin",
        "is_system": True,
        "description": "Grants administrative permissions for an assigned company.",
        "permissions": COMPANY_ADMIN_PERMISSIONS,
    },
    {
        "name": "Company Viewer",
        "is_system": True,
        "description": "Grants read-only permissions for an assigned company.",
        "permissions": COMPANY_VIEWER_PERMISSIONS,
    },
]

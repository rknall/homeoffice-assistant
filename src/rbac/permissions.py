# src/rbac/permissions.py
CORE_PERMISSIONS = [
    # User management
    {"code": "user.read", "module": "core", "description": "Read user information"},
    {
        "code": "user.write.self",
        "module": "core",
        "description": "Update own user profile",
    },
    {
        "code": "user.write.all",
        "module": "core",
        "description": "Update any user profile",
    },
    {
        "code": "user.manage",
        "module": "core",
        "description": "Create, deactivate, and manage users",
    },
    # Company management
    {
        "code": "company.view",
        "module": "core",
        "description": "View company information",
    },
    {
        "code": "company.manage",
        "module": "core",
        "description": "Create and manage companies",
    },
    # Event management
    {"code": "event.read", "module": "core", "description": "View event information"},
    {"code": "event.write", "module": "core", "description": "Create and edit events"},
    {"code": "event.delete", "module": "core", "description": "Delete events"},
    # Expense management
    {"code": "expense.view", "module": "core", "description": "View expenses"},
    {"code": "expense.manage", "module": "core", "description": "Manage expenses"},
    # Integration & System
    {"code": "integration.use", "module": "core", "description": "Use integrations"},
    {
        "code": "integration.config",
        "module": "core",
        "description": "Configure integrations",
    },
    {
        "code": "system.admin",
        "module": "core",
        "description": "Full system administration",
    },
    {
        "code": "system.settings.read",
        "module": "core",
        "description": "Read system settings",
    },
    {
        "code": "system.settings.write",
        "module": "core",
        "description": "Write system settings",
    },
]

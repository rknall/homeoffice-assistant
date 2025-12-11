# User & Role Management (RBAC) Implementation Plan

## Overview

Implement Role-Based Access Control (RBAC) for HomeOffice Assistant based on the specification in `USER_ROLES.md`. This replaces the simple `is_admin` boolean flag with a full RBAC model supporting:
- Users → Roles → Permissions (no direct permission assignments)
- Company-scoped role assignments (global or per-company)
- First user becomes Global Admin via role assignment
- Plugin permission integration with core RBAC

## Key Decisions

- **Merge permissions**: Extend existing `Permission` enum from `src/plugins/base.py` for both plugins and RBAC
- **Full spec implementation**: Complete RBAC with Permission, Role, RolePermission, UserRole tables with company scoping
- **Deprecate is_admin immediately**: Remove flag, convert existing admins to Global Admin role

---

## Phase 1: Data Model Foundation

### New Models to Create

| File | Purpose |
|------|---------|
| `src/models/permission.py` | Permission table (code, module, description) |
| `src/models/role.py` | Role table (name, is_system, description) |
| `src/models/role_permission.py` | Many-to-many Role ↔ Permission |
| `src/models/user_role.py` | User role assignments with optional company_id scope |

### Model Relationships

```
User (1) ←──→ (N) UserRole (N) ←──→ (1) Role (1) ←──→ (N) RolePermission (N) ←──→ (1) Permission
                     │
                     └── company_id (nullable) → Company
```

### UserRole Table Structure
```python
class UserRole(Base, TimestampMixin):
    user_id: ForeignKey("users.id")
    role_id: ForeignKey("roles.id")
    company_id: ForeignKey("companies.id") | None  # null = global scope
    assigned_by: ForeignKey("users.id") | None
    assigned_at: datetime

    # Unique constraint: (user_id, role_id, company_id)
```

### Files to Modify
- `src/models/user.py` - Add `user_roles` relationship
- `src/models/company.py` - Add `user_roles` relationship
- `src/models/__init__.py` - Export new models

---

## Phase 2: Core RBAC Service

### New File: `src/services/rbac_service.py`

Core functions:
```python
def user_has_permission(db, user, permission_code, company_id=None) -> bool
def get_user_permissions(db, user, company_id=None) -> set[str]
def get_user_roles(db, user, company_id=None) -> list[Role]
def assign_role_to_user(db, user_id, role_id, company_id=None, assigned_by=None) -> UserRole
def remove_role_from_user(db, user_id, role_id, company_id=None) -> bool
def get_role_by_name(db, name) -> Role | None
def register_permission(db, code, module, description=None) -> Permission
```

### Permission Check Logic
```python
def user_has_permission(db, user, permission_code, company_id=None):
    if not user.is_active:
        return False

    # 1. Check global roles (company_id is NULL)
    global_perms = get_permissions_from_global_roles(db, user.id)
    if permission_code in global_perms:
        return True

    # 2. Check company-scoped roles if company context provided
    if company_id:
        company_perms = get_permissions_from_company_roles(db, user.id, company_id)
        if permission_code in company_perms:
            return True

    return False
```

---

## Phase 3: Permissions & Roles Seeding

### New Files
- `src/rbac/__init__.py`
- `src/rbac/permissions.py` - Core permission definitions
- `src/rbac/roles.py` - Default role definitions
- `src/services/rbac_seed_service.py` - Seeding logic

### Core Permissions (extending existing plugin permissions)
```python
CORE_PERMISSIONS = [
    # User management
    {"code": "user.read", "module": "core"},
    {"code": "user.write.self", "module": "core"},
    {"code": "user.write.all", "module": "core"},
    {"code": "user.manage", "module": "core"},

    # Company management
    {"code": "company.view", "module": "core"},
    {"code": "company.manage", "module": "core"},

    # Event management
    {"code": "event.read", "module": "core"},
    {"code": "event.write", "module": "core"},
    {"code": "event.delete", "module": "core"},

    # Expense management
    {"code": "expense.view", "module": "core"},
    {"code": "expense.manage", "module": "core"},

    # Notes management
    {"code": "notes.view", "module": "core"},
    {"code": "notes.edit", "module": "core"},

    # Integration & System
    {"code": "integration.use", "module": "core"},
    {"code": "integration.config", "module": "core"},
    {"code": "system.admin", "module": "core"},
    {"code": "system.settings.read", "module": "core"},
    {"code": "system.settings.write", "module": "core"},
]
```

### Default Roles
| Role | Scope | Key Permissions |
|------|-------|-----------------|
| Global Admin | Global | All permissions including `system.admin`, `user.manage` |
| Company Admin | Per-company | `company.view/manage`, `expense.view/manage`, `notes.view/edit` |
| Company Viewer | Per-company | `company.view`, `expense.view`, `notes.view` |

---

## Phase 4: API Layer Changes

### Update `src/api/deps.py`

New dependency factory:
```python
def require_permission(permission_code: str, company_id_param: str | None = None):
    """Dependency for permission-based authorization."""
    def dependency(request, db, current_user):
        company_id = extract_company_id(request, company_id_param)
        if not rbac_service.user_has_permission(db, current_user, permission_code, company_id):
            raise HTTPException(403, f"Permission denied: {permission_code}")
        return current_user
    return dependency
```

Update `get_current_admin`:
```python
def get_current_admin(db, current_user):
    """Verify user has system.admin permission."""
    if not rbac_service.user_has_permission(db, current_user, "system.admin"):
        raise HTTPException(403, "Admin access required")
    return current_user
```

### New File: `src/api/v1/rbac.py`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/rbac/permissions` | List all permissions (admin) |
| GET | `/rbac/roles` | List all roles (admin) |
| GET | `/rbac/roles/{id}` | Get role with permissions (admin) |
| POST | `/rbac/roles` | Create custom role (admin) |
| PUT | `/rbac/roles/{id}` | Update role permissions (admin) |
| DELETE | `/rbac/roles/{id}` | Delete non-system role (admin) |
| GET | `/rbac/users/{id}/roles` | Get user's role assignments (admin) |
| POST | `/rbac/users/{id}/roles` | Assign role to user (admin) |
| DELETE | `/rbac/users/{id}/roles/{role_id}` | Remove role from user (admin) |
| GET | `/rbac/me/permissions` | Get current user's effective permissions |

### Endpoints to Migrate

| Endpoint | Current | New |
|----------|---------|-----|
| `POST /integrations` | `get_current_admin` | `require_permission("integration.config")` |
| `PUT /integrations/{id}` | `get_current_admin` | `require_permission("integration.config")` |
| `DELETE /integrations/{id}` | `get_current_admin` | `require_permission("integration.config")` |
| `PUT /settings/locale` | inline `is_admin` check | `require_permission("system.settings.write")` |
| `POST /backup/*` | `get_current_admin` | `require_permission("system.admin")` |
| Plugin admin endpoints | `get_current_admin` | `require_permission("system.admin")` |

---

## Phase 5: Database Migration

### New Migration: `alembic/versions/xxxx_add_rbac_tables.py`

Steps:
1. Create `permissions` table
2. Create `roles` table
3. Create `role_permissions` table
4. Create `user_roles` table
5. Seed core permissions
6. Seed default roles (Global Admin, Company Admin, Company Viewer)
7. Migrate existing admins: For each user with `is_admin=True`, create UserRole with Global Admin
8. Keep `is_admin` column for rollback safety (remove in future migration)

### Update `src/services/auth_service.py`

```python
def register_user(db, data):
    first_run = is_first_run(db)
    user = User(...)
    db.add(user)
    db.flush()

    if first_run:
        # Assign Global Admin role instead of setting is_admin=True
        global_admin = rbac_service.get_role_by_name(db, "Global Admin")
        rbac_service.assign_role_to_user(db, user.id, global_admin.id)
        set_first_run_complete(db)

    db.commit()
    return user
```

---

## Phase 6: Frontend Changes

### Update Types (`frontend/src/types/index.ts`)
```typescript
interface UserPermissions {
  global_permissions: string[]
  company_permissions: Record<string, string[]>
}
```

### Update Auth Store (`frontend/src/stores/auth.ts`)
```typescript
interface AuthState {
  permissions: string[]
  companyPermissions: Record<string, string[]>
  hasPermission: (code: string, companyId?: string) => boolean
  fetchPermissions: () => Promise<void>
}
```

### Update Sidebar (`frontend/src/components/layout/Sidebar.tsx`)
```typescript
// Replace: user?.is_admin
// With: hasPermission('system.admin')
```

### New Admin Pages
- `frontend/src/pages/settings/RolesSettings.tsx` - Role management
- `frontend/src/pages/settings/UserRolesSettings.tsx` - User role assignments

---

## Phase 7: Plugin Integration

### Update Plugin Permission Registration

When plugin is installed/enabled, register its permissions in the database:
```python
def _register_plugin_permissions(self, plugin, db):
    for perm in plugin.manifest.permissions:
        rbac_service.register_permission(
            db, code=perm.value, module=plugin.id
        )
```

---

## Implementation Milestones

### Milestone 1: Data Model (Est: 2 days)
- [ ] Create Permission, Role, RolePermission, UserRole models
- [ ] Update User and Company models
- [ ] Create Alembic migration
- [ ] Test migration on dev database

### Milestone 2: Service Layer (Est: 2 days)
- [ ] Create rbac_service.py
- [ ] Create rbac_seed_service.py
- [ ] Update auth_service.py for first-user flow
- [ ] Add seeding to app startup

### Milestone 3: API Layer (Est: 2 days)
- [ ] Update deps.py with require_permission
- [ ] Create RBAC API router
- [ ] Migrate existing admin endpoints
- [ ] Add to main router

### Milestone 4: Frontend (Est: 3 days)
- [ ] Update TypeScript types
- [ ] Update auth store with permission helpers
- [ ] Update Sidebar and admin-gated components
- [ ] Create RBAC admin pages

### Milestone 5: Testing (Est: 2 days)
- [ ] Unit tests for rbac_service
- [ ] Integration tests for RBAC API
- [ ] Update test fixtures
- [ ] Migration testing

---

## Critical Files Summary

### New Files
| File | Purpose |
|------|---------|
| `src/models/permission.py` | Permission model |
| `src/models/role.py` | Role model |
| `src/models/role_permission.py` | Role-Permission link |
| `src/models/user_role.py` | User role assignments |
| `src/services/rbac_service.py` | Core RBAC logic |
| `src/services/rbac_seed_service.py` | Seeding logic |
| `src/rbac/permissions.py` | Permission definitions |
| `src/rbac/roles.py` | Role definitions |
| `src/api/v1/rbac.py` | RBAC API endpoints |
| `src/schemas/rbac.py` | Pydantic schemas |
| `alembic/versions/xxxx_add_rbac_tables.py` | Migration |

### Files to Modify
| File | Changes |
|------|---------|
| `src/models/user.py` | Add user_roles relationship |
| `src/models/company.py` | Add user_roles relationship |
| `src/models/__init__.py` | Export new models |
| `src/api/deps.py` | Add require_permission, update get_current_admin |
| `src/api/v1/router.py` | Include RBAC router |
| `src/services/auth_service.py` | First-user Global Admin assignment |
| `src/main.py` | Add RBAC seeding on startup |
| `frontend/src/types/index.ts` | Add permission types |
| `frontend/src/stores/auth.ts` | Add permission helpers |
| `frontend/src/components/layout/Sidebar.tsx` | Use hasPermission |

---

## Risk Mitigation

1. **Rollback**: Keep `is_admin` column, compute dynamically from roles
2. **Data Safety**: Migration seeds data but never deletes
3. **Backward Compatibility**: API continues returning `is_admin` computed from roles
4. **Incremental Rollout**: Can deploy tables before enforcing permissions

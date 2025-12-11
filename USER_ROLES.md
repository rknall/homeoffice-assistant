### User & Role Management Concept (KISS-Friendly)

This document describes a simple, flexible user/role/permission system for your web application. It is designed to:

- Stay as simple as possible (KISS).
- Support:
  - One or more global admins.
  - Companies as a scope.
  - Modules/plugins with their own permissions.
  - Future OAuth2 integration (authentik).
- Avoid a special “superuser gate” in code.  
  Instead: the **first user created becomes a `Global Admin`** via normal roles.

---

### 1. Core Design Principles

1. **Role-based access control (RBAC)**  
   - Users do not get permissions directly.  
   - Users → Roles → Permissions.

2. **Company-scoped roles**  
   - Roles can be assigned globally or for a specific company.
   - Company scoping is the *only* scope dimension for now (no row-level rules).

3. **Global admins via roles, not special flags**  
   - When the app is first initialized and the first user is created, that user is automatically assigned the `Global Admin` role (globally).
   - No `is_superuser` or special bypass logic necessary.
   - You can have multiple global admins by assigning that role to multiple users.

4. **Plugins/modules register permissions, not deep logic**  
   - Each module or plugin declares a set of permission codes (e.g. `expense.view`, `expense.manage`).
   - Core app (or admin) defines roles that bundle those permissions.
   - Admins assign roles to users (globally or per company).

5. **Authentication vs. Authorization**  
   - Authentication (password or OAuth) identifies *who* the user is.
   - Authorization (roles & permissions) decides *what* they can do.
   - Keep them clearly separated.

---

### 2. Data Model Overview

Core entities:

- `User`
- `Company`
- `Permission`
- `Role`
- `RolePermission` (many-to-many)
- `UserRole` (assignment of a role to a user, optionally scoped to a company)

#### 2.1. Users

Represents an account in your system.

Fields (conceptually):

- `id`
- `email`
- `password_hash` (nullable if using only OAuth)
- `is_active` (bool)
- Optional:
  - `display_name`
  - `created_at`, `updated_at`
  - `external_id` / `oauth_subject` (for OAuth integration later)

Notes:

- No `is_superuser` or similar. Global admin behavior is achieved via the `Global Admin` role.

#### 2.2. Companies

Your second organizational unit.

- `Company`
  - `id`
  - `name`
  - Optional metadata: `created_at`, `updated_at`, etc.

Users are tied to companies implicitly via their `UserRole` records.

#### 2.3. Permissions

Atomic capabilities in the system. They are referenced by a **code string**.

- `Permission`
  - `id`
  - `code` (unique string, e.g. `company.view`, `company.manage`, `expense.view`, `expense.manage`, `notes.view`, `notes.edit`, `system.admin`)
  - `module` (string for grouping, e.g. `core`, `expense`, `notes`, `plugin_foo`)
  - Optional: `description`

Conventions for permission codes:

- Use `<module>.<verb>` or `<module>.<resource>.<verb>` patterns.
- Examples:
  - `company.view`, `company.manage`
  - `expense.view`, `expense.manage`
  - `notes.view`, `notes.edit`
  - `user.manage`
  - `system.admin`

#### 2.4. Roles

Named bundles of permissions. This is what admins see and assign.

- `Role`
  - `id`
  - `name` (e.g. `Global Admin`, `Company Admin`, `Company Viewer`, `Expense Manager`, `Expense Viewer`, `Notes Editor`, `Notes Viewer`)
  - `is_system` (bool – true for roles seeded by the system or plugins)
  - Optional:
    - `description`
    - `module` or `origin` (e.g. `core`, `expense-plugin`)

Notes:

- Roles are purely server-side constructs. The UI just needs to list them and let admins assign them.

#### 2.5. RolePermission (Role ↔ Permission)

Link table defining which permissions are granted by a role.

- `RolePermission`
  - `role_id`
  - `permission_id`

#### 2.6. UserRole (User ↔ Role, scoped by Company)

Assignments of roles to users, optionally scoped to a company.

- `UserRole`
  - `user_id`
  - `role_id`
  - `company_id` (nullable)
  - Optional: `assigned_by`, `assigned_at`

Interpretation:

- `company_id = null` → **Global role**. Applies to all companies / global operations.
- `company_id = some_company_id` → **Scoped role**. Applies only inside that company context.

Examples:

- User is global admin:
  - `user_id = 1`, `role_id = GLOBAL_ADMIN_ID`, `company_id = null`
- User can manage company A but not B:
  - `user_id = 2`, `role_id = COMPANY_ADMIN_ID`, `company_id = companyA.id`
- User can only view company B:
  - `user_id = 3`, `role_id = COMPANY_VIEWER_ID`, `company_id = companyB.id`
- User can view company data but not expenses:
  - `user_id = 4`, `role_id = COMPANY_VIEWER_ID`, `company_id = companyX.id`
  - (No expense-related role for that company.)

This structure covers both “user is part of company X” and “what can they do there?” without a separate user–company table.

---

### 3. Permission Check Logic

Everything boils down to checking whether a user, in a given context, has a certain permission.

#### 3.1. Core API

Define a minimal helper (pseudocode):

```python
def user_has_permission(user, permission_code, company_id=None):
    if not user.is_active:
        return False

    # 1) Check global roles (company_id is NULL)
    global_roles = get_roles_for_user(user_id=user.id, company_id=None)
    if permission_code in permissions_from_roles(global_roles):
        return True

    # 2) If a company context is provided, check company-scoped roles
    if company_id is not None:
        company_roles = get_roles_for_user(user_id=user.id, company_id=company_id)
        if permission_code in permissions_from_roles(company_roles):
            return True

    return False
```

Where:

- `get_roles_for_user(user_id, company_id)` returns all `Role` objects that are assigned to that `user_id` for that `company_id` (or globally if `company_id = null`).
- `permissions_from_roles(roles)` returns a set of permission codes from `RolePermission` + `Permission`.

#### 3.2. Usage in Code

- For operations related to a **specific company**:

  - Viewing company information:
    ```python
    user_has_permission(current_user, "company.view", company_id=company.id)
    ```

  - Modifying company configuration:
    ```python
    user_has_permission(current_user, "company.manage", company_id=company.id)
    ```

  - Viewing expenses for that company:
    ```python
    user_has_permission(current_user, "expense.view", company_id=company.id)
    ```

  - Managing expenses for that company:
    ```python
    user_has_permission(current_user, "expense.manage", company_id=company.id)
    ```

- For **global actions** (not tied to a specific company):

  - Admin-level configuration:
    ```python
    user_has_permission(current_user, "system.admin")
    ```

  - Managing users:
    ```python
    user_has_permission(current_user, "user.manage")
    ```

This gives you a consistent, predictable pattern for all authorization checks.

---

### 4. Predefined Roles

Seed a small, opinionated set of roles that cover your current needs.

#### 4.1. Core / Global Roles

1. **Global Admin**
   - Scope: global (`company_id = null`)
   - Intended use: first user created, plus any other full admins.
   - Permissions (example):
     - `system.admin`
     - `user.manage`
     - `company.view`
     - `company.manage`
     - All module-specific permissions, such as:
       - `expense.view`, `expense.manage`
       - `notes.view`, `notes.edit`
       - Others as modules/plugins define them

2. (Optional) **Global Viewer**
   - Scope: global
   - Permissions:
     - `company.view`
     - `expense.view`
     - `notes.view`
   - No management permissions.

#### 4.2. Company-Level Roles

1. **Company Admin**
   - Scope: per-company.
   - Permissions:
     - `company.view`
     - `company.manage`
     - Any module permissions relevant to the company, e.g.:
       - `expense.view`, `expense.manage`
       - `notes.view`, `notes.edit`

2. **Company Viewer**
   - Scope: per-company.
   - Permissions:
     - `company.view`
     - `expense.view`
     - `notes.view`

These two roles alone cover the “manipulate everything for a company vs. just view” use case.

#### 4.3. Module-Specific Roles (Optional Layer of Granularity)

You can optionally define more granular roles if you need more nuanced access:

- **Expense Manager**
  - Permissions:
    - `expense.view`
    - `expense.manage`

- **Expense Viewer**
  - Permissions:
    - `expense.view`

- **Notes Editor**
  - Permissions:
    - `notes.view`
    - `notes.edit`

- **Notes Viewer**
  - Permissions:
    - `notes.view`

These roles can be assigned globally or per company, depending on the `company_id` in `UserRole`.

---

### 5. Module and Plugin Integration

The goal is to keep plugins simple and avoid a combinatorial explosion of special cases.

#### 5.1. Plugin Responsibilities

Each module or plugin should:

- Register its **permissions** on startup or installation.
- Optionally suggest **default roles** that use those permissions.

Example: Expense module permission definition (in some config format):

```json
[
  {
    "code": "expense.view",
    "description": "View expense reports"
  },
  {
    "code": "expense.manage",
    "description": "Create, update, and delete expense reports"
  }
]
```

You would insert or update these in the `Permission` table, with `module = "expense"`.

#### 5.2. Roles vs. Plugins

**(KISS) Approach:**

- Plugins **only define permissions**.
- The core app (and you) define roles that bundle those permissions.
- Example:
  - Expense plugin defines:
    - `expense.view`
    - `expense.manage`
  - Core app has:
    - `Expense Viewer` → `expense.view`
    - `Expense Manager` → `expense.view`, `expense.manage`
    - `Company Admin` → includes both `expense.view` and `expense.manage` (plus others).


### 6. Handling Your Concrete Scenarios

#### 6.1. First User = Global Admin

On first startup, when the application detects that there are **no users yet**:

1. A user signs up / is created via the bootstrap process.
2. The system:
   - Creates the user.
   - Assigns the role:
     - `UserRole(user_id = new_user.id, role_id = GLOBAL_ADMIN_ROLE_ID, company_id = null)`

From that point:

- This user is a `Global Admin`.
- There is no special superuser flag or unique bypass logic. They just have a role with all permissions.
- You can later assign `Global Admin` to other users as needed.

#### 6.2. User Can Manipulate Everything for a Company

For a given company `C`:

- Assign role `Company Admin` with `company_id = C.id`.

Result:

- `user_has_permission(user, "company.manage", company_id=C.id)` → True
- `user_has_permission(user, "expense.manage", company_id=C.id)` → True
- `user_has_permission(user, "notes.edit", company_id=C.id)` → True
- If user has no global or other roles for other companies, they cannot manipulate other companies.

#### 6.3. User Can Only View a Company

For company `C`:

- Assign role `Company Viewer` with `company_id = C.id`.

Result:

- `user_has_permission(user, "company.view", company_id=C.id)` → True
- `user_has_permission(user, "expense.view", company_id=C.id)` → True
- `user_has_permission(user, "notes.view", company_id=C.id)` → True
- No manage/edit permissions.

#### 6.4. User Can View a Company but Not Its Expense Reports

For company `C`:

- Assign a custom role that **only** has `company.view` and maybe `notes.view`, but **not** `expense.view`.
  - Or: use `Company Viewer` plus tweak module-specific roles; the simplest way is often to define a role like `Company Viewer (No Expenses)` if needed.

Then:

- `user_has_permission(user, "company.view", company_id=C.id)` → True
- `user_has_permission(user, "expense.view", company_id=C.id)` → False
- Any expense-related views enforce the latter check and deny access.

#### 6.5. Multiple Global Admins

Any user can be made a global admin by assigning them the `Global Admin` role globally:

- `UserRole(user_id = some_user.id, role_id = GLOBAL_ADMIN_ROLE_ID, company_id = null)`

They will now pass all permission checks that `Global Admin` grants.

---

### 7. OAuth2 (authentik) Integration Concept

Even though implementation will come later, the model already supports OAuth cleanly.

#### 7.1. Authentication Flow (Conceptual)  (NOT IN CURRENT IMPLEMENTATION SCOPE)

On OAuth2 login via authentik:

1. User authenticates with authentik.
2. Your app receives user info (email, subject ID, etc.).
3. Your app:
   - Looks up an existing `User` by email or external ID.
   - If found:
     - Logs them in as that user.
   - If not found:
     - **Auto-provision mode**: create a new `User` record (no roles yet, minimal access until roles are assigned).

Roles & permissions remain entirely internal to your system. OAuth is only used to prove identity.

#### 7.2. Optional Future Enhancement: Mapping OAuth Groups to Roles (NOT IN CURRENT IMPLEMENTATION SCOPE)

Later, you could:

- Configure mappings like:
  - authentik group `app-global-admins` → assign `Global Admin` role globally.
  - authentik group `company-x-managers` → assign `Company Admin` role for company X.

This would be extra logic on top of the same data model, not a change to it.

---

### 8. Initialization & Seeding

On application initialization (migration or first run):

1. **Insert core permissions**:
   - `company.view`, `company.manage`
   - `user.manage`
   - `system.admin` (will manage everything in settings for now, including the integrations)
   - Module permissions (e.g., from Expense & Notes modules):
     - `expense.view`, `expense.manage`
     - `notes.view`, `notes.edit`

2. **Insert core roles**:
   - `Global Admin`
     - Permissions:
       - `system.admin`
       - `user.manage`
       - `company.view`, `company.manage`
       - All module permissions (`expense.*`, `notes.*`, etc.)
   - `Company Admin`
     - Permissions:
       - `company.view`, `company.manage`
       - `expense.view`, `expense.manage`
       - `notes.view`, `notes.edit`
   - `Company Viewer`
     - Permissions:
       - `company.view`
       - `expense.view`
       - `notes.view`
   - (Optional) Additional granular roles:
     - `Expense Manager`, `Expense Viewer`, `Notes Editor`, `Notes Viewer`, etc.

3. **First user bootstrap**:
   - When creating the very first user (detected via “no users exist yet”):
     - Create the `User`.
     - Assign the `Global Admin` role (global scope).

From there, everything else is just normal role assignments.

---

### 9. Summary

- **Users** have **Roles**, roles have **Permissions**.
- **UserRole** optionally stores a `company_id` to scope a role to a company.
- There is no special “superuser” concept in code. Instead:
  - The first user created is automatically assigned the **`Global Admin`** role.
  - Additional global admins are just extra users with the same role.
- Companies are naturally integrated by scoping roles with `company_id`.
- Modules/plugins add new **permissions**; you (or they) define **roles** that bundle them.
- All authorization checks go through a single helper:  
  `user_has_permission(user, permission_code, company_id=None)`.

This keeps the system conceptually simple, while still supporting:

- Companies.
- Modules/plugins.
- Fine-grained permissions.
- Future OAuth2 integration without schema changes.
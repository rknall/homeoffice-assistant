# UUID Migration Plan

## Overview

Migrate all models from `String(36)` to native `UUID(as_uuid=True)` for consistency, performance, and future-proofing. The new RBAC models already use UUID, so we align the rest of the codebase.

## Motivation

- **Database efficiency**: Native UUID is 16 bytes vs 36 bytes for string
- **Index performance**: Binary comparison is faster than string comparison
- **Type safety**: Database enforces UUID format, prevents invalid values
- **PostgreSQL optimization**: PostgreSQL has excellent native UUID support
- **Consistency**: All models use the same pattern (RBAC models already use UUID)

---

## Current State Analysis

### Tables using String(36) IDs (15 tables to migrate)

| Table | Model File |
|-------|------------|
| users | user.py |
| companies | company.py |
| events | event.py |
| expenses | expense.py |
| contacts | contact.py |
| notes | note.py |
| todos | todo.py |
| photo_references | photo_reference.py |
| sessions | session.py |
| integration_configs | integration_config.py |
| company_contacts | company_contact.py |
| email_templates | email_template.py |
| location_images | location_image.py |
| plugin_configs | plugin_config.py |
| plugin_migration_history | plugin_config.py |

### Tables already using UUID (no PK change needed)

| Table | Model File |
|-------|------------|
| roles | role.py |
| user_roles | user_role.py |

### Tables with non-UUID PKs (no change)

| Table | PK Type |
|-------|---------|
| permissions | String(100) - code |
| system_settings | String(100) - key |
| role_permissions | composite (role_id + permission_code) |

---

## Migration Strategy

### Phase 1: Update All Models to Use Native UUID

**Pattern to apply to each model:**

```python
# BEFORE (String pattern):
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

# AFTER (UUID pattern):
import uuid as uuid_lib
from sqlalchemy.dialects.postgresql import UUID

class User(Base):
    id: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
```

**Files to modify:**

1. `src/models/user.py`
2. `src/models/company.py`
3. `src/models/event.py`
4. `src/models/expense.py`
5. `src/models/contact.py`
6. `src/models/note.py`
7. `src/models/todo.py`
8. `src/models/photo_reference.py`
9. `src/models/session.py`
10. `src/models/integration_config.py`
11. `src/models/company_contact.py`
12. `src/models/email_template.py`
13. `src/models/location_image.py`
14. `src/models/plugin_config.py` (both PluginConfig and PluginMigrationHistory)

### Phase 2: Update All Foreign Keys to UUID

All FK columns referencing the above tables must also change:

| Model | FK Column | References |
|-------|-----------|------------|
| Event | user_id | users.id |
| Event | company_id | companies.id |
| Expense | event_id | events.id |
| Contact | event_id | events.id |
| Note | event_id | events.id |
| Todo | event_id | events.id |
| PhotoReference | event_id | events.id |
| Session | user_id | users.id |
| IntegrationConfig | created_by | users.id |
| CompanyContact | company_id | companies.id |
| EmailTemplate | company_id | companies.id |
| UserRole | user_id | users.id |
| UserRole | company_id | companies.id |
| UserRole | assigned_by_id | users.id |

**Note:** UserRole already uses UUID for these FKs - this is correct after migration.

### Phase 3: Create Alembic Migration

**New migration file:** `alembic/versions/xxxx_migrate_to_uuid.py`

Strategy for each table:

1. Create temporary UUID column
2. Convert existing String UUID to native UUID
3. Drop old String column
4. Rename new column to original name
5. Update foreign key constraints

```python
def upgrade():
    # For SQLite (dev): recreate tables with new schema
    # For PostgreSQL (prod): use ALTER COLUMN with USING clause

    # Example for users table:
    # 1. Add new UUID column
    op.add_column('users', sa.Column('id_new', sa.UUID(), nullable=True))

    # 2. Migrate data (convert string to UUID)
    op.execute("""
        UPDATE users
        SET id_new = CAST(id AS UUID)
    """)

    # 3. Drop old constraints, add new ones
    # 4. Drop old column, rename new column
    # ... (detailed for each table)
```

**SQLite Consideration:** SQLite doesn't have native UUID. The migration must handle:

- Development (SQLite): Store UUID as 16-byte BLOB or keep as text
- Production (PostgreSQL): Use native UUID type

### Phase 4: Update Pydantic Schemas

Schemas that return IDs need updating:

```python
# BEFORE:
class UserResponse(BaseModel):
    id: str

# AFTER:
import uuid
class UserResponse(BaseModel):
    id: uuid.UUID

    # Or keep as string for JSON serialization:
    id: str  # UUID auto-converts to string in JSON
```

**Files to check:**

- `src/schemas/user.py`
- `src/schemas/auth.py`
- `src/schemas/company.py`
- `src/schemas/event.py`
- `src/schemas/expense.py`
- All other schema files

### Phase 5: Update API Endpoints

Path parameters expecting UUIDs:

```python
# BEFORE:
@router.get("/{event_id}")
def get_event(event_id: str, ...):

# AFTER:
from uuid import UUID
@router.get("/{event_id}")
def get_event(event_id: UUID, ...):
```

### Phase 6: Update Test Fixtures

**File: `tests/conftest.py`**

```python
import uuid

@pytest.fixture
def rbac_seeded_db(db_session):
    """Seed RBAC data (permissions, roles) before tests."""
    from src.services import rbac_seed_service
    rbac_seed_service.seed_rbac_data(db_session)
    return db_session

@pytest.fixture
def test_user(rbac_seeded_db) -> User:
    """Create a test user."""
    db_session = rbac_seeded_db
    user = User(
        id=uuid.uuid4(),  # Now native UUID
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def admin_user(rbac_seeded_db) -> User:
    """Create an admin test user with Global Admin role."""
    from src.services import rbac_service

    db_session = rbac_seeded_db
    user = User(
        id=uuid.uuid4(),
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    # Assign Global Admin role
    global_admin_role = rbac_service.get_role_by_name(db_session, "Global Admin")
    if global_admin_role:
        rbac_service.assign_role_to_user(db_session, user.id, global_admin_role.id)

    db_session.commit()
    db_session.refresh(user)
    return user
```

---

## Implementation Order

1. **Models** - Update all model files to use UUID
2. **Schemas** - Update Pydantic schemas (most can keep `str` for JSON compat)
3. **Services** - Update any service code that handles IDs
4. **API endpoints** - Update path parameter types
5. **Tests** - Update fixtures and test assertions
6. **Migration** - Create and test alembic migration
7. **Frontend** - No changes needed (UUIDs serialize as strings in JSON)

---

## Files to Modify Summary

| Category | Files |
|----------|-------|
| Models | 14 files in `src/models/` |
| Schemas | ~10 files in `src/schemas/` |
| API | Files in `src/api/v1/` using string IDs in paths |
| Services | `src/services/rbac_service.py` (type hints) |
| Tests | `tests/conftest.py`, integration test files |
| Migration | New file in `alembic/versions/` |

---

## Risk Mitigation

1. **Backup database** before running migration
2. **Test migration** on copy of production data first
3. **Keep String→UUID conversion** in migration for existing data
4. **Frontend unchanged** - JSON serializes UUID as string automatically

---

## Rollback Strategy

If issues occur:

1. Keep the old String columns until migration is verified
2. Create a reverse migration that converts UUID back to String
3. Test rollback on staging before production deployment

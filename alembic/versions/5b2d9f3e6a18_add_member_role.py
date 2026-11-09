"""Add the Member role and assign it to users without a role

Company-scoped permission checks deny everything to a user without any role.
Member grants what such a user could do before, so existing role-less users
keep their access.

Revision ID: 5b2d9f3e6a18
Revises: c61a0e5f8b37
Create Date: 2026-11-08 20:42:14.820012

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b2d9f3e6a18"
down_revision: str | None = "c61a0e5f8b37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MEMBER_ROLE = "Member"
MEMBER_DESCRIPTION = (
    "Default role for regular users: own events, expenses and companies."
)

# Snapshot of the Member permissions at this revision; migrations do not import
# application code, whose lists may change later.
MEMBER_CORE_CODES = (
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
)

# Bundled plugin permissions flagged member_default. Their rows exist only when
# the plugin was installed; plugins installed later link at first registration.
MEMBER_PLUGIN_CODES = (
    "time-tracking.records.read",
    "time-tracking.records.write",
    "time-tracking.records.delete",
    "time-tracking.reports.read",
    "time-tracking.reports.submit",
    "time-tracking.settings.write",
    "example.notes.read",
    "example.notes.write",
    "example.notes.delete",
)

roles = sa.table(
    "roles",
    sa.column("id", sa.Uuid()),
    sa.column("name", sa.String()),
    sa.column("is_system", sa.Boolean()),
    sa.column("description", sa.Text()),
)
permissions = sa.table("permissions", sa.column("code", sa.String()))
role_permissions = sa.table(
    "role_permissions",
    sa.column("role_id", sa.Uuid()),
    sa.column("permission_code", sa.String()),
)
users = sa.table("users", sa.column("id", sa.Uuid()))
user_roles = sa.table(
    "user_roles",
    sa.column("id", sa.Uuid()),
    sa.column("user_id", sa.Uuid()),
    sa.column("role_id", sa.Uuid()),
    sa.column("company_id", sa.Uuid()),
    sa.column("assigned_by_id", sa.Uuid()),
)


def _member_role_id(bind: sa.Connection) -> uuid.UUID | None:
    """Return the id of the Member role, or None when it does not exist."""
    return bind.execute(
        sa.select(roles.c.id).where(roles.c.name == MEMBER_ROLE)
    ).scalar_one_or_none()


def upgrade() -> None:
    bind = op.get_bind()

    role_id = _member_role_id(bind)
    if role_id is None:
        role_id = uuid.uuid4()
        bind.execute(
            roles.insert().values(
                id=role_id,
                name=MEMBER_ROLE,
                is_system=False,
                description=MEMBER_DESCRIPTION,
            )
        )

    wanted = MEMBER_CORE_CODES + MEMBER_PLUGIN_CODES
    existing = set(
        bind.execute(
            sa.select(permissions.c.code).where(permissions.c.code.in_(wanted))
        ).scalars()
    )
    linked = set(
        bind.execute(
            sa.select(role_permissions.c.permission_code).where(
                role_permissions.c.role_id == role_id
            )
        ).scalars()
    )
    links = [
        {"role_id": role_id, "permission_code": code}
        for code in wanted
        if code in existing and code not in linked
    ]
    if links:
        bind.execute(role_permissions.insert(), links)

    role_less = bind.execute(
        sa.select(users.c.id).where(
            ~sa.exists().where(user_roles.c.user_id == users.c.id)
        )
    ).scalars()
    assignments = [
        {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "role_id": role_id,
            "company_id": None,
            "assigned_by_id": None,
        }
        for user_id in role_less
    ]
    if assignments:
        bind.execute(user_roles.insert(), assignments)


def downgrade() -> None:
    bind = op.get_bind()
    role_id = _member_role_id(bind)
    if role_id is None:
        return
    bind.execute(user_roles.delete().where(user_roles.c.role_id == role_id))
    bind.execute(role_permissions.delete().where(role_permissions.c.role_id == role_id))
    bind.execute(roles.delete().where(roles.c.id == role_id))

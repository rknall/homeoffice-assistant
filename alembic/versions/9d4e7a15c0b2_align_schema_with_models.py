"""Align column types with the models

Id and foreign key columns declared VARCHAR(36) or UUID become Uuid (CHAR(32)
on SQLite; the stored 32-char hex values are unchanged), and the
todo_templates category/offset_reference columns become Enum. SQLite cannot
alter a column type, so each table is rebuilt with batch_alter_table, which
copies the rows.

Revision ID: 9d4e7a15c0b2
Revises: 3f8b2c61d9a4
Create Date: 2026-11-08 20:15:24.069406

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d4e7a15c0b2"
down_revision: str | None = "3f8b2c61d9a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("companies", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("company_contacts", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "company_id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("contacts", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "event_id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("email_templates", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "company_id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=True,
        )

    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "user_id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "company_id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("expenses", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "event_id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("integration_configs", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "created_by",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("location_images", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("notes", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "event_id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("photo_references", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "event_id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("plugin_configs", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("plugin_migration_history", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("role_permissions", schema=None) as batch_op:
        batch_op.alter_column(
            "role_id", existing_type=sa.UUID(), type_=sa.Uuid(), existing_nullable=False
        )

    with op.batch_alter_table("roles", schema=None) as batch_op:
        batch_op.alter_column(
            "id", existing_type=sa.UUID(), type_=sa.Uuid(), existing_nullable=False
        )

    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "user_id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("todo_templates", schema=None) as batch_op:
        batch_op.alter_column(
            "category",
            existing_type=sa.VARCHAR(length=50),
            type_=sa.Enum(
                "TRAVEL",
                "ACCOMMODATION",
                "PREPARATION",
                "EQUIPMENT",
                "CONTACTS",
                "FOLLOWUP",
                "OTHER",
                name="todocategory",
            ),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "offset_reference",
            existing_type=sa.VARCHAR(length=20),
            type_=sa.Enum("START_DATE", "END_DATE", name="offsetreference"),
            existing_nullable=False,
        )

    with op.batch_alter_table("todos", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "event_id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )

    with op.batch_alter_table("user_roles", schema=None) as batch_op:
        batch_op.alter_column(
            "id", existing_type=sa.UUID(), type_=sa.Uuid(), existing_nullable=False
        )
        batch_op.alter_column(
            "user_id", existing_type=sa.UUID(), type_=sa.Uuid(), existing_nullable=False
        )
        batch_op.alter_column(
            "role_id", existing_type=sa.UUID(), type_=sa.Uuid(), existing_nullable=False
        )
        batch_op.alter_column(
            "company_id",
            existing_type=sa.UUID(),
            type_=sa.Uuid(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "assigned_by_id",
            existing_type=sa.UUID(),
            type_=sa.Uuid(),
            existing_nullable=True,
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.VARCHAR(length=36),
            type_=sa.Uuid(),
            existing_nullable=False,
        )


def downgrade() -> None:
    # The RBAC id columns keep the Uuid type on downgrade. SQLite gives a
    # declared UUID type NUMERIC affinity, so casting the stored hex ids back
    # would turn them into numbers; the previous models already read Uuid.
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("todos", schema=None) as batch_op:
        batch_op.alter_column(
            "event_id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("todo_templates", schema=None) as batch_op:
        batch_op.alter_column(
            "offset_reference",
            existing_type=sa.Enum("START_DATE", "END_DATE", name="offsetreference"),
            type_=sa.VARCHAR(length=20),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "category",
            existing_type=sa.Enum(
                "TRAVEL",
                "ACCOMMODATION",
                "PREPARATION",
                "EQUIPMENT",
                "CONTACTS",
                "FOLLOWUP",
                "OTHER",
                name="todocategory",
            ),
            type_=sa.VARCHAR(length=50),
            existing_nullable=False,
        )

    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("plugin_migration_history", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("plugin_configs", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("photo_references", schema=None) as batch_op:
        batch_op.alter_column(
            "event_id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("notes", schema=None) as batch_op:
        batch_op.alter_column(
            "event_id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("location_images", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("integration_configs", schema=None) as batch_op:
        batch_op.alter_column(
            "created_by",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("expenses", schema=None) as batch_op:
        batch_op.alter_column(
            "event_id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.alter_column(
            "company_id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("email_templates", schema=None) as batch_op:
        batch_op.alter_column(
            "company_id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("contacts", schema=None) as batch_op:
        batch_op.alter_column(
            "event_id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("company_contacts", schema=None) as batch_op:
        batch_op.alter_column(
            "company_id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

    with op.batch_alter_table("companies", schema=None) as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(length=36),
            existing_nullable=False,
        )

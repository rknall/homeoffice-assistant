"""add_company_contacts

Revision ID: 3a8f2c9d1e5b
Revises: 297d4b88fbfc
Create Date: 2025-12-09

"""

import json
import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a8f2c9d1e5b"
down_revision: str | None = "297d4b88fbfc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create company_contacts table
    op.create_table(
        "company_contacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("department", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contact_types", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("is_main_contact", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_company_contacts_company_id"),
        "company_contacts",
        ["company_id"],
        unique=False,
    )

    # Add new fields to companies table
    op.add_column(
        "companies", sa.Column("webpage", sa.String(length=500), nullable=True)
    )
    op.add_column("companies", sa.Column("address", sa.Text(), nullable=True))
    op.add_column(
        "companies", sa.Column("country", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "companies", sa.Column("logo_path", sa.String(length=500), nullable=True)
    )

    # Add contact_types field to email_templates table
    op.add_column(
        "email_templates",
        sa.Column("contact_types", sa.Text(), nullable=False, server_default="[]"),
    )

    # Data migration: Convert existing expense_recipient to company contact
    # Note: This migrates data from the legacy expense_recipient fields to the new
    # company_contacts table. The legacy fields are dropped in a subsequent migration.
    connection = op.get_bind()

    # Check if companies table has data
    try:
        # Get all companies with expense recipient email
        companies = connection.execute(
            sa.text(
                "SELECT id, name, expense_recipient_email, expense_recipient_name "
                "FROM companies "
                "WHERE expense_recipient_email IS NOT NULL "
                "AND expense_recipient_email != ''"
            )
        ).fetchall()

        # Create company contacts from existing expense recipients
        from datetime import datetime
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        for company in companies:
            contact_id = str(uuid.uuid4())
            contact_name = (
                company[3] if company[3] else company[1]
            )  # Use recipient name or company name
            contact_email = company[2]
            contact_types = json.dumps(["billing"])

            connection.execute(
                sa.text(
                    "INSERT INTO company_contacts "
                    "(id, company_id, name, email, contact_types, "
                    "is_main_contact, created_at, updated_at) "
                    "VALUES (:id, :company_id, :name, :email, "
                    ":contact_types, 1, :created_at, :updated_at)"
                ),
                {
                    "id": contact_id,
                    "company_id": company[0],
                    "name": contact_name,
                    "email": contact_email,
                    "contact_types": contact_types,
                    "created_at": now,
                    "updated_at": now,
                },
            )
    except Exception:
        # If companies table doesn't exist or other error, skip data migration
        pass

    # Update existing expense_report templates to have billing contact type
    try:
        connection.execute(
            sa.text(
                "UPDATE email_templates SET contact_types = :contact_types "
                "WHERE reason = 'expense_report'"
            ),
            {"contact_types": json.dumps(["billing"])},
        )
    except Exception:
        # If email_templates table doesn't exist, skip
        pass


def downgrade() -> None:
    # Remove contact_types from email_templates
    op.drop_column("email_templates", "contact_types")

    # Remove new fields from companies
    op.drop_column("companies", "logo_path")
    op.drop_column("companies", "country")
    op.drop_column("companies", "address")
    op.drop_column("companies", "webpage")

    # Drop company_contacts table
    op.drop_index(op.f("ix_company_contacts_company_id"), table_name="company_contacts")
    op.drop_table("company_contacts")

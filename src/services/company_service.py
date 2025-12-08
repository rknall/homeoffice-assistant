# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company service."""
import json

from sqlalchemy.orm import Session

from src.models import Company
from src.schemas.company import CompanyCreate, CompanyUpdate


def get_companies(db: Session) -> list[Company]:
    """Get all companies."""
    return db.query(Company).order_by(Company.name).all()


def get_company(db: Session, company_id: str) -> Company | None:
    """Get a company by ID."""
    return db.query(Company).filter(Company.id == company_id).first()


def get_company_by_name(db: Session, name: str) -> Company | None:
    """Get a company by name."""
    return db.query(Company).filter(Company.name == name).first()


def get_company_by_email(db: Session, email: str, exclude_id: str | None = None) -> Company | None:
    """Get a company by expense recipient email, optionally excluding a specific company ID."""
    query = db.query(Company).filter(Company.expense_recipient_email == email)
    if exclude_id:
        query = query.filter(Company.id != exclude_id)
    return query.first()


def create_company(db: Session, data: CompanyCreate) -> Company:
    """Create a new company."""
    company = Company(
        name=data.name,
        type=data.type,
        paperless_storage_path_id=data.paperless_storage_path_id,
        expense_recipient_email=data.expense_recipient_email,
        expense_recipient_name=data.expense_recipient_name,
        report_recipients=json.dumps(data.report_recipients) if data.report_recipients else None,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def update_company(db: Session, company: Company, data: CompanyUpdate) -> Company:
    """Update an existing company."""
    if data.name is not None:
        company.name = data.name
    if data.type is not None:
        company.type = data.type
    if data.paperless_storage_path_id is not None:
        company.paperless_storage_path_id = data.paperless_storage_path_id
    if data.expense_recipient_email is not None:
        company.expense_recipient_email = data.expense_recipient_email
    if data.expense_recipient_name is not None:
        company.expense_recipient_name = data.expense_recipient_name
    if data.report_recipients is not None:
        company.report_recipients = json.dumps(data.report_recipients)

    db.commit()
    db.refresh(company)
    return company


def delete_company(db: Session, company: Company) -> None:
    """Delete a company."""
    db.delete(company)
    db.commit()


def company_to_response_dict(company: Company) -> dict:
    """Convert company to response dict with parsed JSON fields."""
    return {
        "id": company.id,
        "name": company.name,
        "type": company.type,
        "paperless_storage_path_id": company.paperless_storage_path_id,
        "expense_recipient_email": company.expense_recipient_email,
        "expense_recipient_name": company.expense_recipient_name,
        "report_recipients": json.loads(company.report_recipients)
        if company.report_recipients
        else None,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
    }

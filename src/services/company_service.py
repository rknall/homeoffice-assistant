# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company service."""

import json
import uuid

from sqlalchemy.orm import Session

from src.models import Company
from src.plugins.events import AppEvent, event_bus
from src.schemas.company import CompanyCreate, CompanyUpdate


def get_companies(db: Session) -> list[Company]:
    """Get all companies."""
    return db.query(Company).order_by(Company.name).all()


def get_company(db: Session, company_id: uuid.UUID) -> Company | None:
    """Get a company by ID."""
    return db.query(Company).filter(Company.id == company_id).first()


def get_company_by_name(db: Session, name: str) -> Company | None:
    """Get a company by name."""
    return db.query(Company).filter(Company.name == name).first()


def create_company(db: Session, data: CompanyCreate) -> Company:
    """Create a new company."""
    company = Company(
        name=data.name,
        type=data.type,
        paperless_storage_path_id=data.paperless_storage_path_id,
        report_recipients=json.dumps(data.report_recipients)
        if data.report_recipients
        else None,
        webpage=data.webpage,
        address=data.address,
        country=data.country,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # Publish company created event
    event_bus.publish_sync(
        AppEvent.COMPANY_CREATED,
        {
            "company_id": str(company.id),
            "name": company.name,
            "type": company.type.value if company.type else None,
        },
    )

    return company


def update_company(db: Session, company: Company, data: CompanyUpdate) -> Company:
    """Update an existing company."""
    if data.name is not None:
        company.name = data.name
    if data.type is not None:
        company.type = data.type
    if data.paperless_storage_path_id is not None:
        company.paperless_storage_path_id = data.paperless_storage_path_id
    if data.report_recipients is not None:
        company.report_recipients = json.dumps(data.report_recipients)
    if data.webpage is not None:
        company.webpage = data.webpage
    if data.address is not None:
        company.address = data.address
    if data.country is not None:
        company.country = data.country

    db.commit()
    db.refresh(company)

    # Publish company updated event
    event_bus.publish_sync(
        AppEvent.COMPANY_UPDATED,
        {
            "company_id": str(company.id),
            "name": company.name,
            "type": company.type.value if company.type else None,
        },
    )

    return company


def delete_company(db: Session, company: Company) -> None:
    """Delete a company."""
    db.delete(company)
    db.commit()


def company_to_response_dict(company: Company, include_contacts: bool = True) -> dict:
    """Convert company to response dict with parsed JSON fields."""
    from src.services.company_contact_service import contact_to_response

    result = {
        "id": company.id,
        "name": company.name,
        "type": company.type,
        "paperless_storage_path_id": company.paperless_storage_path_id,
        "report_recipients": json.loads(company.report_recipients)
        if company.report_recipients
        else None,
        "webpage": company.webpage,
        "address": company.address,
        "country": company.country,
        "logo_path": company.logo_path,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
    }

    if include_contacts:
        result["contacts"] = [contact_to_response(c) for c in company.contacts]
    else:
        result["contacts"] = []

    return result

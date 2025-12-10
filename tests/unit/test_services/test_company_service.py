# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for company_service."""

from src.models import CompanyContact
from src.models.enums import CompanyType
from src.schemas.company import CompanyCreate, CompanyUpdate
from src.services import company_service


def test_create_and_get_company(db_session):
    data = CompanyCreate(name="Acme", type=CompanyType.EMPLOYER)
    company = company_service.create_company(db_session, data)

    assert company.id is not None
    assert company_service.get_company(db_session, company.id) == company
    assert company_service.get_company_by_name(db_session, "Acme") == company
    companies = company_service.get_companies(db_session)
    assert len(companies) == 1


def test_update_and_delete_company(db_session):
    company = company_service.create_company(
        db_session, CompanyCreate(name="Acme", type=CompanyType.EMPLOYER)
    )

    update = CompanyUpdate(
        name="Acme Corp",
        paperless_storage_path_id=42,
        report_recipients=[{"name": "Finance", "email": "fin@example.com"}],
        webpage="https://acme.example.com",
        address="Main St",
        country="AT",
    )
    updated = company_service.update_company(db_session, company, update)

    assert updated.name == "Acme Corp"
    assert updated.paperless_storage_path_id == 42
    assert updated.report_recipients is not None
    assert updated.webpage == "https://acme.example.com"
    assert updated.address == "Main St"
    assert updated.country == "AT"

    company_service.delete_company(db_session, updated)
    assert company_service.get_company(db_session, updated.id) is None


def test_company_to_response_dict_includes_contacts(db_session):
    company = company_service.create_company(
        db_session, CompanyCreate(name="Acme", type=CompanyType.EMPLOYER)
    )
    contact = CompanyContact(
        company_id=company.id,
        name="John Doe",
        email="john@example.com",
        phone="123",
        contact_types='["billing"]',
        is_main_contact=True,
    )
    db_session.add(contact)
    db_session.commit()

    response = company_service.company_to_response_dict(company)
    assert response["name"] == "Acme"
    assert response["report_recipients"] is None
    assert len(response["contacts"]) == 1

    no_contacts = company_service.company_to_response_dict(company, include_contacts=False)
    assert no_contacts["contacts"] == []

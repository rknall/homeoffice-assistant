# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for company_contact_service."""

from src.models import Company
from src.models.enums import CompanyType, ContactType
from src.schemas.company_contact import CompanyContactCreate, CompanyContactUpdate
from src.services import company_contact_service


def create_company(db_session) -> Company:
    company = Company(name="Acme", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def create_contact(
    db_session, company_id: str, name: str, contact_types=None, is_main=False
):
    data = CompanyContactCreate(
        name=name,
        email=f"{name}@example.com",
        contact_types=contact_types or [ContactType.BILLING],
        is_main_contact=is_main,
    )
    return company_contact_service.create_contact(db_session, company_id, data)


def test_create_contact_sets_main_for_first_contact(db_session):
    company = create_company(db_session)
    contact = create_contact(db_session, company.id, "first", is_main=False)

    assert contact.is_main_contact is True


def test_create_contact_unsets_existing_main(db_session):
    company = create_company(db_session)
    first = create_contact(db_session, company.id, "first", is_main=True)
    second = create_contact(
        db_session, company.id, "second", contact_types=[ContactType.HR], is_main=True
    )

    db_session.refresh(first)
    assert first.is_main_contact is False
    assert second.is_main_contact is True


def test_update_contact_fields(db_session):
    company = create_company(db_session)
    contact = create_contact(db_session, company.id, "first", is_main=True)
    other = create_contact(db_session, company.id, "other", is_main=False)

    update = CompanyContactUpdate(
        name="Updated",
        phone="123",
        contact_types=[ContactType.SALES],
        is_main_contact=False,
    )
    updated = company_contact_service.update_contact(db_session, contact, update)

    assert updated.name == "Updated"
    assert updated.phone == "123"
    assert updated.is_main_contact is False
    db_session.refresh(other)
    assert other.is_main_contact is True


def test_set_main_contact(db_session):
    company = create_company(db_session)
    contact = create_contact(db_session, company.id, "first", is_main=False)

    updated = company_contact_service.set_main_contact(db_session, contact)
    assert updated.is_main_contact is True


def test_delete_contact_reassigns_main(db_session):
    company = create_company(db_session)
    first = create_contact(db_session, company.id, "first", is_main=True)
    second = create_contact(db_session, company.id, "second", is_main=False)

    company_contact_service.delete_contact(db_session, first)
    db_session.refresh(second)
    assert second.is_main_contact is True


def test_getters_and_filters(db_session):
    company = create_company(db_session)
    contact = create_contact(
        db_session,
        company.id,
        "first",
        contact_types=[ContactType.BILLING, ContactType.SUPPORT],
        is_main=True,
    )

    contacts = company_contact_service.get_contacts(db_session, company.id)
    assert len(contacts) == 1
    assert company_contact_service.get_contact(db_session, contact.id) == contact
    assert (
        company_contact_service.get_contact_by_company(
            db_session, company.id, contact.id
        )
        == contact
    )
    main = company_contact_service.get_main_contact(db_session, company.id)
    assert main == contact

    filtered = company_contact_service.get_contacts_by_type(
        db_session, company.id, [ContactType.SUPPORT]
    )
    assert filtered == [contact]


def test_validate_contact_types_exist(db_session):
    company = create_company(db_session)
    create_contact(
        db_session, company.id, "first", contact_types=[ContactType.BILLING], is_main=True
    )

    ok, missing = company_contact_service.validate_contact_types_exist(
        db_session, company.id, [ContactType.BILLING]
    )
    assert ok is True
    assert missing == []

    ok, missing = company_contact_service.validate_contact_types_exist(
        db_session, company.id, [ContactType.SALES]
    )
    assert ok is False
    assert missing == [ContactType.SALES]


def test_contact_to_response(db_session):
    company = create_company(db_session)
    contact = create_contact(db_session, company.id, "first", is_main=True)
    response = company_contact_service.contact_to_response(contact)
    assert response.name == "first"
    assert ContactType.BILLING in response.contact_types

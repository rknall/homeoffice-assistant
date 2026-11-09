# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the document reference functions of document_reference_service."""

import uuid
from datetime import date

from src.models import Company, Event, User
from src.models.enums import CompanyType
from src.schemas.document_reference import (
    DocumentReferenceCreate,
    DocumentReferenceUpdate,
)
from src.security import get_password_hash
from src.services import document_reference_service as service


def make_event(db_session) -> Event:
    user = User(
        username="refuser",
        email="refuser@example.com",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    company = Company(name="Acme", type=CompanyType.EMPLOYER)
    db_session.add_all([user, company])
    db_session.commit()
    event = Event(
        name="Expo",
        start_date=date(2025, 5, 1),
        end_date=date(2025, 5, 5),
        company_id=company.id,
        user_id=user.id,
    )
    db_session.add(event)
    db_session.commit()
    return event


def test_create_list_and_duplicate(db_session):
    event = make_event(db_session)
    data = DocumentReferenceCreate(paperless_doc_id=5, title="Doc")

    created = service.create_reference(db_session, event, data)

    assert created is not None
    assert service.list_references(db_session, event) == [created]
    assert service.create_reference(db_session, event, data) is None


def test_update_changes_only_given_fields(db_session):
    event = make_event(db_session)
    created = service.create_reference(
        db_session,
        event,
        DocumentReferenceCreate(paperless_doc_id=5, title="Doc", notes="n"),
    )

    updated = service.update_reference(
        db_session,
        event,
        created.id,
        DocumentReferenceUpdate(include_in_report=True),
    )

    assert updated.include_in_report is True
    assert updated.notes == "n"
    assert (
        service.update_reference(
            db_session, event, uuid.uuid4(), DocumentReferenceUpdate()
        )
        is None
    )


def test_delete_reference(db_session):
    event = make_event(db_session)
    created = service.create_reference(
        db_session, event, DocumentReferenceCreate(paperless_doc_id=5, title="Doc")
    )

    assert service.delete_reference(db_session, event, created.id) is True
    assert service.delete_reference(db_session, event, created.id) is False
    assert service.list_references(db_session, event) == []

# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Paperless documents and document references of an event."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.integrations.base import DocumentProvider
from src.models import DocumentReference, Event, Expense
from src.schemas.document_reference import (
    DocumentReferenceCreate,
    DocumentReferenceUpdate,
)
from src.services import integration_service


async def get_event_documents(
    db: Session, event: Event, provider: DocumentProvider
) -> list[dict[str, Any]]:
    """Fetch the Paperless documents matched to an event.

    Matches by the company's storage path and the event's custom field value,
    the same filter the event detail page lists.

    Args:
        db: Database session.
        event: The event whose documents are listed.
        provider: An open document provider.

    Returns:
        The matching documents as returned by the provider.
    """
    custom_field_name = "Trip"
    paperless_config = integration_service.get_active_document_provider(db)
    if paperless_config:
        decrypted = integration_service.get_decrypted_config(paperless_config)
        custom_field_name = decrypted.get("custom_field_name", "Trip")
    custom_field = await provider.get_custom_field_by_name(custom_field_name)
    custom_field_id = custom_field["id"] if custom_field else None

    storage_path_id = event.company.paperless_storage_path_id if event.company else None

    return await provider.get_documents_for_event(
        storage_path_id=storage_path_id,
        custom_field_id=custom_field_id,
        custom_field_value=event.paperless_custom_field_value,
    )


async def document_belongs_to_event(
    db: Session, event: Event, document_id: int, provider: DocumentProvider
) -> bool:
    """Check that a Paperless document is linked to an event.

    A document belongs to the event when it is referenced by one of the
    event's document references or expenses, or when Paperless lists it for
    the event. The local links are checked first, so Paperless is only asked
    when they do not match.

    Args:
        db: Database session.
        event: The event the document must belong to.
        document_id: The Paperless document id.
        provider: An open document provider.

    Returns:
        True when the document belongs to the event.
    """
    reference_id = db.scalar(
        select(DocumentReference.id).where(
            DocumentReference.event_id == event.id,
            DocumentReference.paperless_doc_id == document_id,
        )
    )
    if reference_id is not None:
        return True

    expense_id = db.scalar(
        select(Expense.id).where(
            Expense.event_id == event.id,
            Expense.paperless_doc_id == document_id,
        )
    )
    if expense_id is not None:
        return True

    documents = await get_event_documents(db, event, provider)
    return any(doc.get("id") == document_id for doc in documents)


def list_references(db: Session, event: Event) -> list[DocumentReference]:
    """Return the event's document references, newest first."""
    return list(
        db.scalars(
            select(DocumentReference)
            .where(DocumentReference.event_id == event.id)
            .order_by(DocumentReference.created_at.desc())
        )
    )


def create_reference(
    db: Session, event: Event, data: DocumentReferenceCreate
) -> DocumentReference | None:
    """Link a Paperless document to the event.

    Returns:
        The new reference, or None when the document is already linked.
    """
    existing = db.scalars(
        select(DocumentReference).where(
            DocumentReference.event_id == event.id,
            DocumentReference.paperless_doc_id == data.paperless_doc_id,
        )
    ).first()
    if existing:
        return None
    reference = DocumentReference(
        event_id=event.id,
        paperless_doc_id=data.paperless_doc_id,
        title=data.title,
        original_filename=data.original_filename,
        notes=data.notes,
        document_type=data.document_type,
        include_in_report=data.include_in_report,
    )
    db.add(reference)
    db.commit()
    db.refresh(reference)
    return reference


def _get_reference(
    db: Session, event: Event, reference_id: uuid.UUID
) -> DocumentReference | None:
    """Return the event's reference with this id, or None."""
    return db.scalars(
        select(DocumentReference).where(
            DocumentReference.id == reference_id,
            DocumentReference.event_id == event.id,
        )
    ).first()


def update_reference(
    db: Session,
    event: Event,
    reference_id: uuid.UUID,
    data: DocumentReferenceUpdate,
) -> DocumentReference | None:
    """Apply the given fields to a reference; None when it is not found."""
    reference = _get_reference(db, event, reference_id)
    if reference is None:
        return None
    if data.notes is not None:
        reference.notes = data.notes
    if data.document_type is not None:
        reference.document_type = data.document_type
    if data.include_in_report is not None:
        reference.include_in_report = data.include_in_report
    db.commit()
    db.refresh(reference)
    return reference


def delete_reference(db: Session, event: Event, reference_id: uuid.UUID) -> bool:
    """Unlink a reference from the event; False when it is not found."""
    reference = _get_reference(db, event, reference_id)
    if reference is None:
        return False
    db.delete(reference)
    db.commit()
    return True

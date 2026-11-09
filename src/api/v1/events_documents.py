# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Event document endpoints: Paperless documents and document references."""

import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.api.deps import require_event_permission
from src.api.provider_errors import provider_errors
from src.api.v1._http import content_disposition
from src.database import get_db
from src.integrations.base import DocumentProvider
from src.integrations.failure import failure_category
from src.integrations.llm import LlmError
from src.models import DocumentReference, Event
from src.models.enums import IntegrationType
from src.schemas.document_reference import (
    DocumentReferenceCreate,
    DocumentReferenceResponse,
    DocumentReferenceUpdate,
)
from src.schemas.expense import ExpenseScanResult
from src.schemas.integration import DocumentResponse
from src.services import (
    document_reference_service,
    expense_scan_service,
    integration_service,
)
from src.services.integration_service import ProviderError

router = APIRouter()
logger = logging.getLogger(__name__)

read_event = require_event_permission("event.read")
write_event = require_event_permission("event.write")
scan_event_expense = require_event_permission("expense.manage")


async def _ensure_event_document(
    db: Session, event: Event, document_id: int, provider: DocumentProvider
) -> None:
    """Raise 404 unless the Paperless document belongs to the event.

    Without this check any user could reach any Paperless document through
    one of their own events.

    Raises:
        HTTPException: 404 when the document is not linked to the event, 502
            when Paperless cannot be asked.
    """
    try:
        linked = await document_reference_service.document_belongs_to_event(
            db, event, document_id, provider
        )
    except httpx.HTTPError as e:
        logger.error("Failed to check document %s in Paperless: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to check document in Paperless: {failure_category(e)}",
        ) from e
    if not linked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )


@router.get("/{event_id}/documents", response_model=list[DocumentResponse])
async def get_event_documents(
    db: Session = Depends(get_db),
    event: Event = Depends(read_event),
) -> list[DocumentResponse]:
    """Get documents from Paperless associated with this event."""
    try:
        async with integration_service.open_active_provider(
            db, IntegrationType.PAPERLESS
        ) as provider:
            documents = await document_reference_service.get_event_documents(
                db, event, provider
            )
    except ProviderError:
        return []  # No Paperless integration configured or usable
    return [DocumentResponse(**doc) for doc in documents]


@router.delete(
    "/{event_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_event_document(
    document_id: int,
    db: Session = Depends(get_db),
    event: Event = Depends(write_event),
) -> None:
    """Delete a document from Paperless.

    Warning: This permanently deletes the document!
    """
    with provider_errors():
        async with integration_service.open_active_provider(
            db, IntegrationType.PAPERLESS
        ) as provider:
            await _ensure_event_document(db, event, document_id, provider)
            success = await provider.delete_document(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document from Paperless",
        )


@router.get("/{event_id}/documents/{document_id}/preview")
async def get_document_preview(
    document_id: int,
    db: Session = Depends(get_db),
    event: Event = Depends(read_event),
) -> Response:
    """Get document content for preview from Paperless."""
    with provider_errors():
        async with integration_service.open_active_provider(
            db, IntegrationType.PAPERLESS
        ) as provider:
            await _ensure_event_document(db, event, document_id, provider)
            try:
                content, filename, content_type = await provider.download_document(
                    document_id
                )
            except httpx.HTTPError as e:
                logger.error("Failed to download document %s: %s", document_id, e)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to download document",
                ) from e

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": content_disposition(filename, "inline"),
        },
    )


@router.post(
    "/{event_id}/documents/{document_id}/scan-expense",
    response_model=ExpenseScanResult,
)
async def scan_document_for_expense(
    document_id: int,
    db: Session = Depends(get_db),
    event: Event = Depends(scan_event_expense),
) -> ExpenseScanResult:
    """Extract expense fields from a document's OCR text via the LLM integration."""
    with provider_errors():
        async with (
            integration_service.open_active_provider(db, IntegrationType.LLM) as llm,
            integration_service.open_active_provider(
                db, IntegrationType.PAPERLESS
            ) as paperless,
        ):
            await _ensure_event_document(db, event, document_id, paperless)
            try:
                content = await paperless.get_document_content(document_id)
            except httpx.HTTPError as e:
                logger.error("Failed to fetch text of document %s: %s", document_id, e)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch document text",
                ) from e
            if not content.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Document has no OCR text to scan",
                )
            try:
                raw = await llm.extract_expense(content)
            except LlmError as e:
                logger.error("Expense scan of document %s failed: %s", document_id, e)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Expense scan failed: {failure_category(e)}",
                ) from e

    return expense_scan_service.validate_extraction(raw)


# Document Reference endpoints (non-expense documents linked to events)


@router.get(
    "/{event_id}/document-references",
    response_model=list[DocumentReferenceResponse],
)
def list_document_references(
    db: Session = Depends(get_db),
    event: Event = Depends(read_event),
) -> list[DocumentReference]:
    """List all document references linked to an event."""
    return document_reference_service.list_references(db, event)


@router.post(
    "/{event_id}/document-references",
    response_model=DocumentReferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document_reference(
    data: DocumentReferenceCreate,
    db: Session = Depends(get_db),
    event: Event = Depends(write_event),
) -> DocumentReference:
    """Link a Paperless document to an event."""
    reference = document_reference_service.create_reference(db, event, data)
    if reference is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document already linked to this event",
        )
    return reference


@router.put(
    "/{event_id}/document-references/{reference_id}",
    response_model=DocumentReferenceResponse,
)
def update_document_reference(
    reference_id: uuid.UUID,
    data: DocumentReferenceUpdate,
    db: Session = Depends(get_db),
    event: Event = Depends(write_event),
) -> DocumentReference:
    """Update a document reference's notes, type, or include_in_report flag."""
    reference = document_reference_service.update_reference(
        db, event, reference_id, data
    )
    if reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document reference not found",
        )
    return reference


@router.delete(
    "/{event_id}/document-references/{reference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document_reference(
    reference_id: uuid.UUID,
    db: Session = Depends(get_db),
    event: Event = Depends(write_event),
) -> None:
    """Unlink a document from an event (does not delete from Paperless)."""
    if not document_reference_service.delete_reference(db, event, reference_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document reference not found",
        )

# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Note API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import require_event_permission
from src.database import get_db
from src.models import Event, Note
from src.schemas.note import NoteCreate, NoteResponse, NoteUpdate
from src.services import note_service

router = APIRouter()


def _get_note_or_404(db: Session, note_id: uuid.UUID, event: Event) -> Note:
    """Load a note of the event or raise 404."""
    note = note_service.get_note_for_event(db, note_id, event.id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    return note


@router.get("/{event_id}/notes", response_model=list[NoteResponse])
def list_notes(
    event: Event = Depends(require_event_permission("event.read")),
) -> list[NoteResponse]:
    """List notes for an event."""
    return [NoteResponse.model_validate(n) for n in event.notes]


@router.post(
    "/{event_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
    data: NoteCreate,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.write")),
) -> NoteResponse:
    """Create a new note for an event."""
    note = note_service.create_note(db, event.id, data)
    return NoteResponse.model_validate(note)


@router.get("/{event_id}/notes/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: uuid.UUID,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.read")),
) -> NoteResponse:
    """Get a specific note."""
    return NoteResponse.model_validate(_get_note_or_404(db, note_id, event))


@router.put("/{event_id}/notes/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: uuid.UUID,
    data: NoteUpdate,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.write")),
) -> NoteResponse:
    """Update a note."""
    note = _get_note_or_404(db, note_id, event)
    return NoteResponse.model_validate(note_service.update_note(db, note, data))


@router.delete("/{event_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: uuid.UUID,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.write")),
) -> None:
    """Delete a note."""
    note_service.delete_note(db, _get_note_or_404(db, note_id, event))

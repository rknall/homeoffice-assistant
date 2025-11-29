# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Note API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import Note, User
from src.schemas.note import NoteCreate, NoteResponse, NoteUpdate
from src.services import event_service

router = APIRouter()


@router.get("/{event_id}/notes", response_model=list[NoteResponse])
def list_notes(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NoteResponse]:
    """List notes for an event."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    return [NoteResponse.model_validate(n) for n in event.notes]


@router.post(
    "/{event_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
    event_id: str,
    data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteResponse:
    """Create a new note for an event."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    note = Note(
        event_id=event_id,
        content=data.content,
        note_type=data.note_type,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteResponse.model_validate(note)


@router.get("/{event_id}/notes/{note_id}", response_model=NoteResponse)
def get_note(
    event_id: str,
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteResponse:
    """Get a specific note."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    note = db.query(Note).filter(Note.id == note_id, Note.event_id == event_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    return NoteResponse.model_validate(note)


@router.put("/{event_id}/notes/{note_id}", response_model=NoteResponse)
def update_note(
    event_id: str,
    note_id: str,
    data: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteResponse:
    """Update a note."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    note = db.query(Note).filter(Note.id == note_id, Note.event_id == event_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    db.commit()
    db.refresh(note)
    return NoteResponse.model_validate(note)


@router.delete("/{event_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    event_id: str,
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a note."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    note = db.query(Note).filter(Note.id == note_id, Note.event_id == event_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    db.delete(note)
    db.commit()

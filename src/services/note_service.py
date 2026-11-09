# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Note service for managing event notes."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from src.models import Note
from src.schemas.note import NoteCreate, NoteUpdate


def get_note_for_event(
    db: Session, note_id: uuid.UUID, event_id: uuid.UUID
) -> Note | None:
    """Get a note that belongs to a specific event.

    Args:
        db: Database session.
        note_id: Note UUID.
        event_id: Event UUID the note must belong to.

    Returns:
        The note, or None when it does not exist on that event.
    """
    return db.scalar(
        sa.select(Note).where(Note.id == note_id, Note.event_id == event_id)
    )


def create_note(db: Session, event_id: uuid.UUID, data: NoteCreate) -> Note:
    """Create a note on an event.

    Args:
        db: Database session.
        event_id: Event UUID.
        data: Note fields.

    Returns:
        The created note.
    """
    note = Note(event_id=event_id, content=data.content, note_type=data.note_type)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def update_note(db: Session, note: Note, data: NoteUpdate) -> Note:
    """Apply the fields set in ``data`` to a note.

    Args:
        db: Database session.
        note: Note to update.
        data: Fields to change; unset fields are left as they are.

    Returns:
        The updated note.
    """
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, note: Note) -> None:
    """Delete a note.

    Args:
        db: Database session.
        note: Note to delete.
    """
    db.delete(note)
    db.commit()

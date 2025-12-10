# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Example plugin API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User

from .models import ExampleNote
from .schemas import NoteCreate, NoteResponse, NoteUpdate, PluginInfoResponse

router = APIRouter(tags=["example-plugin"])


@router.get("/info", response_model=PluginInfoResponse)
def get_plugin_info(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> PluginInfoResponse:
    """Get information about the example plugin."""
    note_count = db.query(ExampleNote).count()
    return PluginInfoResponse(
        plugin_id="example",
        plugin_name="Example Plugin",
        version="1.0.0",
        greeting="Hello from the Example Plugin!",
        note_count=note_count,
    )


@router.get("/notes", response_model=list[NoteResponse])
def list_notes(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[NoteResponse]:
    """List all notes."""
    notes = db.query(ExampleNote).order_by(ExampleNote.created_at.desc()).all()
    return [
        NoteResponse(
            id=str(note.id),
            title=note.title,
            content=note.content,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
        for note in notes
    ]


@router.post("/notes", response_model=NoteResponse, status_code=201)
def create_note(
    data: NoteCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> NoteResponse:
    """Create a new note."""
    note = ExampleNote(title=data.title, content=data.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteResponse(
        id=str(note.id),
        title=note.title,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> NoteResponse:
    """Get a specific note."""
    note = db.query(ExampleNote).filter(ExampleNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteResponse(
        id=str(note.id),
        title=note.title,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.put("/notes/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: str,
    data: NoteUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> NoteResponse:
    """Update a note."""
    note = db.query(ExampleNote).filter(ExampleNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if data.title is not None:
        note.title = data.title
    if data.content is not None:
        note.content = data.content

    db.commit()
    db.refresh(note)
    return NoteResponse(
        id=str(note.id),
        title=note.title,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
    """Delete a note."""
    note = db.query(ExampleNote).filter(ExampleNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()

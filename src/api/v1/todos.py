# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Todo API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import Todo, User
from src.schemas.todo import TodoCreate, TodoResponse, TodoUpdate
from src.services import event_service

router = APIRouter()


@router.get("/{event_id}/todos", response_model=list[TodoResponse])
def list_todos(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TodoResponse]:
    """List todos for an event."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    return [TodoResponse.model_validate(t) for t in event.todos]


@router.post(
    "/{event_id}/todos",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_todo(
    event_id: uuid.UUID,
    data: TodoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoResponse:
    """Create a new todo for an event."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    todo = Todo(
        event_id=event_id,
        title=data.title,
        description=data.description,
        due_date=data.due_date,
        category=data.category,
        completed=False,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return TodoResponse.model_validate(todo)


@router.get("/{event_id}/todos/{todo_id}", response_model=TodoResponse)
def get_todo(
    event_id: uuid.UUID,
    todo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoResponse:
    """Get a specific todo."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.event_id == event_id).first()
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    return TodoResponse.model_validate(todo)


@router.put("/{event_id}/todos/{todo_id}", response_model=TodoResponse)
def update_todo(
    event_id: uuid.UUID,
    todo_id: uuid.UUID,
    data: TodoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoResponse:
    """Update a todo."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.event_id == event_id).first()
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)
    db.commit()
    db.refresh(todo)
    return TodoResponse.model_validate(todo)


@router.delete("/{event_id}/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    event_id: uuid.UUID,
    todo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a todo."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.event_id == event_id).first()
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )

    db.delete(todo)
    db.commit()

# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Todo API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import Todo, User
from src.schemas.todo import TodoCreate, TodoResponse, TodoUpdate
from src.schemas.todo_template import (
    ApplyTemplatesRequest,
    ApplyTemplatesResponse,
    TemplateSetWithComputedDates,
)
from src.services import event_service, todo_template_service

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


@router.get(
    "/{event_id}/todos/templates",
    response_model=list[TemplateSetWithComputedDates],
)
def get_templates_for_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TemplateSetWithComputedDates]:
    """Get template sets with computed due dates for an event."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return todo_template_service.get_template_sets_with_computed_dates(
        db, current_user.id, event_id
    )


@router.post(
    "/{event_id}/todos/from-templates",
    response_model=ApplyTemplatesResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_templates_to_event(
    event_id: uuid.UUID,
    data: ApplyTemplatesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplyTemplatesResponse:
    """Apply selected templates to an event, creating todos."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    count, created_ids = todo_template_service.apply_templates_to_event(
        db, event_id, data.template_ids
    )

    return ApplyTemplatesResponse(
        created_count=count,
        todos_created=created_ids,
    )


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

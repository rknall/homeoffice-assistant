# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Todo API endpoints."""

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import require_event_permission, require_permission
from src.database import get_db
from src.models import Event, Todo, User
from src.schemas.todo import TodoCreate, TodoResponse, TodoUpdate
from src.schemas.todo_template import (
    ApplyTemplatesRequest,
    ApplyTemplatesResponse,
    TemplateSetWithComputedDates,
)
from src.services import rbac_service, todo_service, todo_template_service

router = APIRouter()

# Todos across events, mounted at /todos.
due_router = APIRouter()


def _get_todo_or_404(db: Session, todo_id: uuid.UUID, event: Event) -> Todo:
    """Load a todo of the event or raise 404."""
    todo = todo_service.get_todo_for_event(db, todo_id, event.id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    return todo


@router.get("/{event_id}/todos", response_model=list[TodoResponse])
def list_todos(
    event: Event = Depends(require_event_permission("event.read")),
) -> list[TodoResponse]:
    """List todos for an event."""
    return [TodoResponse.model_validate(t) for t in event.todos]


@router.get(
    "/{event_id}/todos/templates",
    response_model=list[TemplateSetWithComputedDates],
)
def get_templates_for_event(
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.read")),
) -> list[TemplateSetWithComputedDates]:
    """Get template sets with computed due dates for an event."""
    return todo_template_service.get_template_sets_with_computed_dates(
        db, event.user_id, event.id
    )


@router.post(
    "/{event_id}/todos/from-templates",
    response_model=ApplyTemplatesResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_templates_to_event(
    data: ApplyTemplatesRequest,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.write")),
) -> ApplyTemplatesResponse:
    """Apply selected templates to an event, creating todos."""
    count, created_ids = todo_template_service.apply_templates_to_event(
        db, event.id, data.template_ids
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
    data: TodoCreate,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.write")),
) -> TodoResponse:
    """Create a new todo for an event."""
    todo = todo_service.create_todo(db, event.id, data)
    return TodoResponse.model_validate(todo)


@router.get("/{event_id}/todos/{todo_id}", response_model=TodoResponse)
def get_todo(
    todo_id: uuid.UUID,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.read")),
) -> TodoResponse:
    """Get a specific todo."""
    return TodoResponse.model_validate(_get_todo_or_404(db, todo_id, event))


@router.put("/{event_id}/todos/{todo_id}", response_model=TodoResponse)
def update_todo(
    todo_id: uuid.UUID,
    data: TodoUpdate,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.write")),
) -> TodoResponse:
    """Update a todo."""
    todo = _get_todo_or_404(db, todo_id, event)
    return TodoResponse.model_validate(todo_service.update_todo(db, todo, data))


@router.delete("/{event_id}/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: uuid.UUID,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.write")),
) -> None:
    """Delete a todo."""
    todo_service.delete_todo(db, _get_todo_or_404(db, todo_id, event))


@due_router.get("", response_model=list[TodoResponse])
def list_due_todos(
    due_from: datetime.date,
    due_to: datetime.date,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("event.read", company_id_param="company_id")
    ),
) -> list[TodoResponse]:
    """List the todos due in a date range on the user's own events.

    Both ends of the range are inclusive. Only events of companies in which
    the user holds ``event.read`` are included.
    """
    if due_from > due_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="due_from must not be after due_to",
        )
    companies = rbac_service.companies_with_permission(db, current_user, "event.read")
    todos = todo_service.list_due_todos(
        db, current_user.id, due_from, due_to, companies
    )
    return [TodoResponse.model_validate(t) for t in todos]

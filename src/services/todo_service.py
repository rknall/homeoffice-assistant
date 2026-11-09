# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Todo service for managing event todos."""

import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.models.enums import TodoCategory
from src.models.event import Event
from src.models.todo import Todo
from src.schemas.todo import TodoCreate, TodoUpdate


def get_todo_for_event(
    db: Session, todo_id: uuid.UUID, event_id: uuid.UUID
) -> Todo | None:
    """Get a todo that belongs to a specific event.

    Args:
        db: Database session.
        todo_id: Todo UUID.
        event_id: Event UUID the todo must belong to.

    Returns:
        The todo, or None when it does not exist on that event.
    """
    return db.scalar(
        sa.select(Todo).where(Todo.id == todo_id, Todo.event_id == event_id)
    )


def list_due_todos(
    db: Session,
    user_id: uuid.UUID,
    start: datetime.date,
    end: datetime.date,
    company_ids: set[uuid.UUID] | None,
) -> list[Todo]:
    """List the todos due in a date range on a user's own events.

    Args:
        db: Database session.
        user_id: Owner of the events whose todos are listed.
        start: First due date included.
        end: Last due date included.
        company_ids: Companies whose events are included; None means every
            company, an empty set means none.

    Returns:
        Todos ordered by due date and title.
    """
    if company_ids is not None and not company_ids:
        return []
    query = (
        sa.select(Todo)
        .join(Event, Todo.event_id == Event.id)
        .where(Event.user_id == user_id, Todo.due_date.between(start, end))
        .order_by(Todo.due_date, Todo.title)
    )
    if company_ids is not None:
        query = query.where(Event.company_id.in_(company_ids))
    return list(db.scalars(query))


def create_todo(db: Session, event_id: uuid.UUID, data: TodoCreate) -> Todo:
    """Create an open todo on an event.

    Args:
        db: Database session.
        event_id: Event UUID.
        data: Todo fields.

    Returns:
        The created todo.
    """
    todo = Todo(event_id=event_id, completed=False, **data.model_dump())
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


def update_todo(db: Session, todo: Todo, data: TodoUpdate) -> Todo:
    """Apply the fields set in ``data`` to a todo.

    Args:
        db: Database session.
        todo: Todo to update.
        data: Fields to change; unset fields are left as they are.

    Returns:
        The updated todo.
    """
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)
    db.commit()
    db.refresh(todo)
    return todo


def delete_todo(db: Session, todo: Todo) -> None:
    """Delete a todo.

    Args:
        db: Database session.
        todo: Todo to delete.
    """
    db.delete(todo)
    db.commit()


def auto_complete_report_todos(db: Session, event_id: uuid.UUID) -> int:
    """Mark report-related todos as complete when expense report is sent/generated.

    Marks todos as complete if they match:
    - Category is FOLLOWUP
    - Title contains keywords like 'report', 'submit', 'send', 'expense'

    Args:
        db: Database session
        event_id: Event UUID

    Returns:
        Number of todos marked as complete
    """
    # Find incomplete todos that match report-related criteria
    todos = (
        db.query(Todo)
        .filter(
            Todo.event_id == event_id,
            Todo.completed.is_(False),
            or_(
                Todo.category == TodoCategory.FOLLOWUP,
                Todo.title.ilike("%report%"),
                Todo.title.ilike("%submit%"),
                Todo.title.ilike("%send%"),
                Todo.title.ilike("%expense%"),
            ),
        )
        .all()
    )

    # Mark matching todos as complete
    count = 0
    for todo in todos:
        todo.completed = True
        count += 1

    if count > 0:
        db.commit()

    return count

# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Todo service for managing event todos."""

import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.models.enums import TodoCategory
from src.models.todo import Todo


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
            Todo.completed == False,  # noqa: E712 - SQLAlchemy requires == for comparison
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

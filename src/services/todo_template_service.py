# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Todo template service for managing and applying todo templates."""

import uuid
from datetime import date, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.models.enums import OffsetReference, TodoCategory
from src.models.event import Event
from src.models.todo import Todo
from src.models.todo_template import TodoTemplate
from src.schemas.todo_template import (
    TemplateSetResponse,
    TemplateSetWithComputedDates,
    TodoTemplateCreate,
    TodoTemplateResponse,
    TodoTemplateUpdate,
    TodoTemplateWithComputedDate,
)


def calculate_due_date(
    template: TodoTemplate,
    event_start: date,
    event_end: date,
) -> date:
    """Calculate the due date for a template based on event dates.

    Args:
        template: The todo template
        event_start: Event start date
        event_end: Event end date

    Returns:
        Calculated due date
    """
    if template.offset_reference == OffsetReference.START_DATE:
        reference_date = event_start
    else:
        reference_date = event_end

    return reference_date + timedelta(days=template.days_offset)


def get_templates_for_user(
    db: Session,
    user_id: uuid.UUID,
) -> list[TodoTemplate]:
    """Get all templates visible to a user (global + user's own).

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        List of TodoTemplate objects
    """
    return (
        db.query(TodoTemplate)
        .filter(
            or_(
                TodoTemplate.is_global == True,  # noqa: E712
                TodoTemplate.user_id == user_id,
            )
        )
        .order_by(
            TodoTemplate.template_set_name,
            TodoTemplate.display_order,
            TodoTemplate.title,
        )
        .all()
    )


def get_template_sets_for_user(
    db: Session,
    user_id: uuid.UUID,
) -> list[TemplateSetResponse]:
    """Get all template sets with their templates for a user.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        List of TemplateSetResponse objects grouped by set name
    """
    templates = get_templates_for_user(db, user_id)

    # Group by template_set_name
    sets_dict: dict[str, list[TodoTemplate]] = {}
    for template in templates:
        if template.template_set_name not in sets_dict:
            sets_dict[template.template_set_name] = []
        sets_dict[template.template_set_name].append(template)

    result = []
    for set_name, set_templates in sets_dict.items():
        # Determine if set is global (all templates in set are global)
        is_global = all(t.is_global for t in set_templates)
        result.append(
            TemplateSetResponse(
                name=set_name,
                templates=[
                    TodoTemplateResponse.model_validate(t) for t in set_templates
                ],
                is_global=is_global,
            )
        )

    return result


def get_template_sets_with_computed_dates(
    db: Session,
    user_id: uuid.UUID,
    event_id: uuid.UUID,
) -> list[TemplateSetWithComputedDates]:
    """Get template sets with computed due dates for a specific event.

    Args:
        db: Database session
        user_id: User UUID
        event_id: Event UUID

    Returns:
        List of TemplateSetWithComputedDates objects
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return []

    templates = get_templates_for_user(db, user_id)

    # Group by template_set_name with computed dates
    sets_dict: dict[str, list[TodoTemplateWithComputedDate]] = {}
    for template in templates:
        computed_date = calculate_due_date(
            template,
            event.start_date,
            event.end_date,
        )

        template_with_date = TodoTemplateWithComputedDate(
            **TodoTemplateResponse.model_validate(template).model_dump(),
            computed_due_date=computed_date,
        )

        if template.template_set_name not in sets_dict:
            sets_dict[template.template_set_name] = []
        sets_dict[template.template_set_name].append(template_with_date)

    result = []
    for set_name, set_templates in sets_dict.items():
        is_global = all(t.is_global for t in set_templates)
        result.append(
            TemplateSetWithComputedDates(
                name=set_name,
                templates=set_templates,
                is_global=is_global,
            )
        )

    return result


def get_template_by_id(
    db: Session,
    template_id: uuid.UUID,
) -> TodoTemplate | None:
    """Get a template by ID.

    Args:
        db: Database session
        template_id: Template UUID

    Returns:
        TodoTemplate or None
    """
    return db.query(TodoTemplate).filter(TodoTemplate.id == template_id).first()


def create_template(
    db: Session,
    user_id: uuid.UUID,
    data: TodoTemplateCreate,
) -> TodoTemplate:
    """Create a new user template.

    Args:
        db: Database session
        user_id: User UUID
        data: Template creation data

    Returns:
        Created TodoTemplate
    """
    template = TodoTemplate(
        title=data.title,
        description=data.description,
        category=data.category,
        days_offset=data.days_offset,
        offset_reference=data.offset_reference,
        template_set_name=data.template_set_name,
        is_global=False,
        user_id=user_id,
        display_order=data.display_order,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_template(
    db: Session,
    template: TodoTemplate,
    data: TodoTemplateUpdate,
) -> TodoTemplate:
    """Update an existing template.

    Args:
        db: Database session
        template: Existing template
        data: Update data

    Returns:
        Updated TodoTemplate
    """
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    db.commit()
    db.refresh(template)
    return template


def delete_template(
    db: Session,
    template: TodoTemplate,
) -> None:
    """Delete a template.

    Args:
        db: Database session
        template: Template to delete
    """
    db.delete(template)
    db.commit()


def apply_templates_to_event(
    db: Session,
    event_id: uuid.UUID,
    template_ids: list[uuid.UUID],
) -> tuple[int, list[uuid.UUID]]:
    """Apply selected templates to an event, creating todos.

    Args:
        db: Database session
        event_id: Event UUID
        template_ids: List of template UUIDs to apply

    Returns:
        Tuple of (count of created todos, list of created todo UUIDs)
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return (0, [])

    templates = (
        db.query(TodoTemplate).filter(TodoTemplate.id.in_(template_ids)).all()
    )

    created_ids: list[uuid.UUID] = []
    for template in templates:
        due_date = calculate_due_date(
            template,
            event.start_date,
            event.end_date,
        )

        todo = Todo(
            event_id=event_id,
            title=template.title,
            description=template.description,
            due_date=due_date,
            completed=False,
            category=template.category,
        )
        db.add(todo)
        db.flush()
        created_ids.append(todo.id)

    db.commit()
    return (len(created_ids), created_ids)


def seed_default_templates(db: Session) -> int:
    """Seed default global templates if they don't exist.

    Args:
        db: Database session

    Returns:
        Number of templates created
    """
    # Check if global templates already exist
    existing = (
        db.query(TodoTemplate)
        .filter(TodoTemplate.is_global == True)  # noqa: E712
        .first()
    )
    if existing:
        return 0

    default_templates = [
        # Business Trip Set
        TodoTemplate(
            title="Book flights",
            description="Book flights for the trip",
            category=TodoCategory.TRAVEL,
            days_offset=-14,
            offset_reference=OffsetReference.START_DATE,
            template_set_name="Business Trip",
            is_global=True,
            user_id=None,
            display_order=1,
        ),
        TodoTemplate(
            title="Book accommodation",
            description="Reserve hotel or accommodation",
            category=TodoCategory.ACCOMMODATION,
            days_offset=-14,
            offset_reference=OffsetReference.START_DATE,
            template_set_name="Business Trip",
            is_global=True,
            user_id=None,
            display_order=2,
        ),
        TodoTemplate(
            title="Prepare travel documents",
            description="Passport, visa, itinerary, boarding passes",
            category=TodoCategory.PREPARATION,
            days_offset=-3,
            offset_reference=OffsetReference.START_DATE,
            template_set_name="Business Trip",
            is_global=True,
            user_id=None,
            display_order=3,
        ),
        TodoTemplate(
            title="Submit expense report",
            description="Compile receipts and submit expense report",
            category=TodoCategory.FOLLOWUP,
            days_offset=7,
            offset_reference=OffsetReference.END_DATE,
            template_set_name="Business Trip",
            is_global=True,
            user_id=None,
            display_order=4,
        ),
        # Conference Event Set
        TodoTemplate(
            title="Register for conference",
            description="Complete registration and payment",
            category=TodoCategory.PREPARATION,
            days_offset=-30,
            offset_reference=OffsetReference.START_DATE,
            template_set_name="Conference Event",
            is_global=True,
            user_id=None,
            display_order=1,
        ),
        TodoTemplate(
            title="Review agenda and sessions",
            description="Plan which sessions to attend",
            category=TodoCategory.PREPARATION,
            days_offset=-7,
            offset_reference=OffsetReference.START_DATE,
            template_set_name="Conference Event",
            is_global=True,
            user_id=None,
            display_order=2,
        ),
        TodoTemplate(
            title="Prepare business cards",
            description="Print or order business cards for networking",
            category=TodoCategory.EQUIPMENT,
            days_offset=-7,
            offset_reference=OffsetReference.START_DATE,
            template_set_name="Conference Event",
            is_global=True,
            user_id=None,
            display_order=3,
        ),
        TodoTemplate(
            title="Follow up with contacts",
            description="Send follow-up emails to new connections",
            category=TodoCategory.CONTACTS,
            days_offset=3,
            offset_reference=OffsetReference.END_DATE,
            template_set_name="Conference Event",
            is_global=True,
            user_id=None,
            display_order=4,
        ),
    ]

    for template in default_templates:
        db.add(template)

    db.commit()
    return len(default_templates)

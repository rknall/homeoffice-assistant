# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Todo Template API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.schemas.todo_template import (
    TemplateSetResponse,
    TodoTemplateCreate,
    TodoTemplateResponse,
    TodoTemplateUpdate,
)
from src.services import todo_template_service

router = APIRouter()


@router.get("", response_model=list[TemplateSetResponse])
def list_template_sets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TemplateSetResponse]:
    """List all template sets visible to the user (global + user's own)."""
    return todo_template_service.get_template_sets_for_user(db, current_user.id)


@router.get("/all", response_model=list[TodoTemplateResponse])
def list_all_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TodoTemplateResponse]:
    """List all templates visible to the user as a flat list."""
    templates = todo_template_service.get_templates_for_user(db, current_user.id)
    return [TodoTemplateResponse.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=TodoTemplateResponse)
def get_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoTemplateResponse:
    """Get a specific template."""
    template = todo_template_service.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Check access: global templates or user's own
    if not template.is_global and template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return TodoTemplateResponse.model_validate(template)


@router.post(
    "",
    response_model=TodoTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    data: TodoTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoTemplateResponse:
    """Create a new user template."""
    template = todo_template_service.create_template(db, current_user.id, data)
    return TodoTemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=TodoTemplateResponse)
def update_template(
    template_id: uuid.UUID,
    data: TodoTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoTemplateResponse:
    """Update a user template."""
    template = todo_template_service.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Cannot edit global templates or other users' templates
    if template.is_global:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot edit global templates",
        )

    if template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    updated = todo_template_service.update_template(db, template, data)
    return TodoTemplateResponse.model_validate(updated)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a user template."""
    template = todo_template_service.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Cannot delete global templates or other users' templates
    if template.is_global:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete global templates",
        )

    if template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    todo_template_service.delete_template(db, template)

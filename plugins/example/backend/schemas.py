# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Example plugin Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NoteBase(BaseModel):
    """Base schema for notes."""

    title: str
    content: str | None = None


class NoteCreate(NoteBase):
    """Schema for creating a note."""

    pass


class NoteUpdate(BaseModel):
    """Schema for updating a note."""

    title: str | None = None
    content: str | None = None


class NoteResponse(NoteBase):
    """Schema for note responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class PluginInfoResponse(BaseModel):
    """Response schema for plugin info endpoint."""

    plugin_id: str
    plugin_name: str
    version: str
    greeting: str
    note_count: int

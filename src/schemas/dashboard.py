# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Dashboard schemas for aggregated summary data."""

import datetime
import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, PlainSerializer

# Annotated type that serializes Decimal as float for JSON responses
SerializedDecimal = Annotated[Decimal, PlainSerializer(lambda x: float(x), return_type=float)]


class EventsByStatus(BaseModel):
    """Count of events by computed status."""

    upcoming: int = 0
    active: int = 0
    past: int = 0


class UpcomingEvent(BaseModel):
    """Preview of an upcoming event for dashboard."""

    id: uuid.UUID
    name: str
    company_name: str | None
    start_date: datetime.date
    end_date: datetime.date
    city: str | None
    country: str | None
    days_until: int


class EventNeedingReport(BaseModel):
    """Event that has expenses but no report generated."""

    event_id: uuid.UUID
    event_name: str
    company_name: str | None
    expense_count: int
    total_amount: SerializedDecimal
    currency: str


class IncompleteTodo(BaseModel):
    """Incomplete todo item with event context."""

    id: uuid.UUID
    title: str
    due_date: datetime.date | None
    event_id: uuid.UUID
    event_name: str
    is_overdue: bool


class ExpenseByCategory(BaseModel):
    """Expense breakdown by category."""

    category: str
    amount: SerializedDecimal
    percentage: float


class ExpenseSummary(BaseModel):
    """Summary of expenses for a time period."""

    total: SerializedDecimal
    by_category: list[ExpenseByCategory]
    period_days: int = 90


class DashboardSummary(BaseModel):
    """Complete dashboard summary response."""

    events_by_status: EventsByStatus
    upcoming_events: list[UpcomingEvent]
    events_needing_reports: list[EventNeedingReport]
    incomplete_todos: list[IncompleteTodo]
    expense_summary: ExpenseSummary

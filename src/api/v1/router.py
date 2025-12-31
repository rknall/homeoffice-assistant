# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Main API router for v1 endpoints."""

from fastapi import APIRouter

from src.api.v1 import (
    auth,
    backup,
    companies,
    company_contacts,
    contacts,
    currencies,
    dashboard,
    email_templates,
    events,
    expenses,
    integrations,
    locations,
    notes,
    photos,
    plugins,
    rbac,
    reports,
    settings,
    submissions,
    todo_templates,
    todos,
    users,
)

api_router = APIRouter()

# Auth routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Dashboard routes
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# Currency routes
api_router.include_router(currencies.router, tags=["currencies"])

# Integration routes
api_router.include_router(
    integrations.router, prefix="/integrations", tags=["integrations"]
)

# Company routes
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])

# Company contact routes (nested under companies)
api_router.include_router(
    company_contacts.router, prefix="/companies", tags=["company-contacts"]
)

# Event routes
api_router.include_router(events.router, prefix="/events", tags=["events"])

# Expense routes (nested under events)
api_router.include_router(expenses.router, prefix="/events", tags=["expenses"])

# Submission routes (nested under events)
api_router.include_router(submissions.router, prefix="/events", tags=["submissions"])

# Contact routes (nested under events)
api_router.include_router(contacts.router, prefix="/events", tags=["contacts"])

# Note routes (nested under events)
api_router.include_router(notes.router, prefix="/events", tags=["notes"])

# Todo routes (nested under events)
api_router.include_router(todos.router, prefix="/events", tags=["todos"])

# Todo template routes
api_router.include_router(
    todo_templates.router, prefix="/todo-templates", tags=["todo-templates"]
)

# Report routes (nested under events)
api_router.include_router(reports.router, prefix="/events", tags=["reports"])

# Settings routes
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])

# Email template routes
api_router.include_router(
    email_templates.router, prefix="/email-templates", tags=["email-templates"]
)

# Backup routes
api_router.include_router(backup.router, prefix="/backup", tags=["backup"])

# Location routes
api_router.include_router(locations.router)

# Photo routes (nested under events)
api_router.include_router(photos.router, prefix="/events", tags=["photos"])

# Plugin management routes
api_router.include_router(plugins.router)

# RBAC routes
api_router.include_router(rbac.router)

# User management routes
api_router.include_router(users.router, tags=["users"])

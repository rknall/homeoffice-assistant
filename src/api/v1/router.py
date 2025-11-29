"""Main API router for v1 endpoints."""
from fastapi import APIRouter

from src.api.v1 import (
    auth,
    companies,
    contacts,
    events,
    expenses,
    integrations,
    notes,
    reports,
    settings,
    todos,
)

api_router = APIRouter()

# Auth routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Integration routes
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])

# Company routes
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])

# Event routes
api_router.include_router(events.router, prefix="/events", tags=["events"])

# Expense routes (nested under events)
api_router.include_router(expenses.router, prefix="/events", tags=["expenses"])

# Contact routes (nested under events)
api_router.include_router(contacts.router, prefix="/events", tags=["contacts"])

# Note routes (nested under events)
api_router.include_router(notes.router, prefix="/events", tags=["notes"])

# Todo routes (nested under events)
api_router.include_router(todos.router, prefix="/events", tags=["todos"])

# Report routes (nested under events)
api_router.include_router(reports.router, prefix="/events", tags=["reports"])

# Settings routes
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])

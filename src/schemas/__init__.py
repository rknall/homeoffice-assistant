# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Pydantic schemas package."""
from src.schemas.auth import (
    AuthResponse,
    AuthStatusResponse,
    LoginRequest,
    RegisterRequest,
)
from src.schemas.common import (
    HealthResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
)
from src.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
)
from src.schemas.contact import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
)
from src.schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateResponse,
    EmailTemplateUpdate,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateReason,
    TemplateVariableInfo,
)
from src.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
)
from src.schemas.expense import (
    ExpenseBulkUpdate,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
)
from src.schemas.integration import (
    IntegrationConfigCreate,
    IntegrationConfigResponse,
    IntegrationConfigUpdate,
    IntegrationTestResult,
    IntegrationTypeInfo,
    StoragePathResponse,
    TagResponse,
)
from src.schemas.note import (
    NoteCreate,
    NoteResponse,
    NoteUpdate,
)
from src.schemas.todo import (
    TodoCreate,
    TodoResponse,
    TodoUpdate,
)
from src.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Auth
    "LoginRequest",
    "RegisterRequest",
    "AuthResponse",
    "AuthStatusResponse",
    # Common
    "PaginatedResponse",
    "PaginationMeta",
    "HealthResponse",
    "MessageResponse",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    # Company
    "CompanyCreate",
    "CompanyUpdate",
    "CompanyResponse",
    # Event
    "EventCreate",
    "EventUpdate",
    "EventResponse",
    "EventDetailResponse",
    # Expense
    "ExpenseCreate",
    "ExpenseUpdate",
    "ExpenseResponse",
    "ExpenseBulkUpdate",
    # Contact
    "ContactCreate",
    "ContactUpdate",
    "ContactResponse",
    # Note
    "NoteCreate",
    "NoteUpdate",
    "NoteResponse",
    # Todo
    "TodoCreate",
    "TodoUpdate",
    "TodoResponse",
    # Integration
    "IntegrationConfigCreate",
    "IntegrationConfigUpdate",
    "IntegrationConfigResponse",
    "IntegrationTypeInfo",
    "IntegrationTestResult",
    "StoragePathResponse",
    "TagResponse",
    # Email Template
    "EmailTemplateCreate",
    "EmailTemplateUpdate",
    "EmailTemplateResponse",
    "TemplatePreviewRequest",
    "TemplatePreviewResponse",
    "TemplateReason",
    "TemplateVariableInfo",
]

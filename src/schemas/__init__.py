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
from src.schemas.company_calendar import (
    CalendarSyncResult,
    CompanyCalendarCreate,
    CompanyCalendarResponse,
    CompanyCalendarUpdate,
)
from src.schemas.company_contact import (
    CompanyContactCreate,
    CompanyContactResponse,
    CompanyContactUpdate,
    TemplateContactValidation,
)
from src.schemas.contact import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
)
from src.schemas.document_reference import (
    DocumentReferenceCreate,
    DocumentReferenceResponse,
    DocumentReferenceUpdate,
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
from src.schemas.location import (
    LocationImageResponse,
    LocationSuggestion,
)
from src.schemas.note import (
    NoteCreate,
    NoteResponse,
    NoteUpdate,
)
from src.schemas.photo import (
    PhotoAsset,
    PhotoReferenceCreate,
    PhotoReferenceResponse,
    PhotoReferenceUpdate,
)
from src.schemas.todo import (
    TodoCreate,
    TodoResponse,
    TodoUpdate,
)
from src.schemas.todo_template import (
    ApplyTemplatesRequest,
    ApplyTemplatesResponse,
    TemplateSetResponse,
    TemplateSetWithComputedDates,
    TodoTemplateCreate,
    TodoTemplateResponse,
    TodoTemplateUpdate,
    TodoTemplateWithComputedDate,
)
from src.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Todo Template
    "ApplyTemplatesRequest",
    "ApplyTemplatesResponse",
    "AuthResponse",
    "AuthStatusResponse",
    # Company Calendar
    "CalendarSyncResult",
    "CompanyCalendarCreate",
    "CompanyCalendarResponse",
    "CompanyCalendarUpdate",
    # Company Contact
    "CompanyContactCreate",
    "CompanyContactResponse",
    "CompanyContactUpdate",
    # Company
    "CompanyCreate",
    "CompanyResponse",
    "CompanyUpdate",
    # Contact
    "ContactCreate",
    "ContactResponse",
    "ContactUpdate",
    # Document Reference
    "DocumentReferenceCreate",
    "DocumentReferenceResponse",
    "DocumentReferenceUpdate",
    # Email Template
    "EmailTemplateCreate",
    "EmailTemplateResponse",
    "EmailTemplateUpdate",
    # Event
    "EventCreate",
    "EventDetailResponse",
    "EventResponse",
    "EventUpdate",
    "ExpenseBulkUpdate",
    # Expense
    "ExpenseCreate",
    "ExpenseResponse",
    "ExpenseUpdate",
    "HealthResponse",
    # Integration
    "IntegrationConfigCreate",
    "IntegrationConfigResponse",
    "IntegrationConfigUpdate",
    "IntegrationTestResult",
    "IntegrationTypeInfo",
    "LocationImageResponse",
    # Location
    "LocationSuggestion",
    # Auth
    "LoginRequest",
    "MessageResponse",
    # Note
    "NoteCreate",
    "NoteResponse",
    "NoteUpdate",
    # Common
    "PaginatedResponse",
    "PaginationMeta",
    # Photo
    "PhotoAsset",
    "PhotoReferenceCreate",
    "PhotoReferenceResponse",
    "PhotoReferenceUpdate",
    "RegisterRequest",
    "StoragePathResponse",
    "TagResponse",
    "TemplateContactValidation",
    "TemplatePreviewRequest",
    "TemplatePreviewResponse",
    "TemplateReason",
    "TemplateSetResponse",
    "TemplateSetWithComputedDates",
    "TemplateVariableInfo",
    # Todo
    "TodoCreate",
    "TodoResponse",
    "TodoTemplateCreate",
    "TodoTemplateResponse",
    "TodoTemplateUpdate",
    "TodoTemplateWithComputedDate",
    "TodoUpdate",
    # User
    "UserCreate",
    "UserResponse",
    "UserUpdate",
]

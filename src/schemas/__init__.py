# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Pydantic schemas package."""

from src.schemas.auth import (
    AuthResponse,
    AuthStatusResponse,
    LoginRequest,
    RegisterRequest,
)
from src.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
)
from src.schemas.company_calendar import (
    CompanyCalendarCreate,
    CompanyCalendarResponse,
    CompanyCalendarUpdate,
)
from src.schemas.company_contact import (
    CompanyContactCreate,
    CompanyContactResponse,
    CompanyContactUpdate,
)
from src.schemas.contact import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
)
from src.schemas.currency import (
    CurrencyResponse,
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
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
)
from src.schemas.holiday_calendar import (
    CountryInfo,
    HolidayCalendarCreate,
    HolidayCalendarResponse,
    HolidayCalendarUpdate,
    HolidayEntry,
    HolidaysResponse,
    SupportedCountriesResponse,
)
from src.schemas.integration import (
    IntegrationConfigCreate,
    IntegrationConfigResponse,
    IntegrationConfigUpdate,
    IntegrationTestResult,
    IntegrationTypeInfo,
    StoragePathResponse,
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
from src.schemas.report import (
    GenerateReportRequest,
    SendReportRequest,
    SendReportResponse,
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
    # Holiday Calendar
    "CountryInfo",
    "CurrencyResponse",
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
    # Expense
    "ExpenseCreate",
    "ExpenseResponse",
    "ExpenseUpdate",
    "GenerateReportRequest",
    "HolidayCalendarCreate",
    "HolidayCalendarResponse",
    "HolidayCalendarUpdate",
    "HolidayEntry",
    "HolidaysResponse",
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
    # Note
    "NoteCreate",
    "NoteResponse",
    "NoteUpdate",
    # Common
    # Photo
    "PhotoAsset",
    "PhotoReferenceCreate",
    "PhotoReferenceResponse",
    "PhotoReferenceUpdate",
    "RegisterRequest",
    "SendReportRequest",
    "SendReportResponse",
    "StoragePathResponse",
    "SupportedCountriesResponse",
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

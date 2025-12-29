# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Enumeration types for database models."""

from enum import Enum


class CompanyType(str, Enum):
    """Company type enumeration."""

    EMPLOYER = "employer"
    THIRD_PARTY = "third_party"


class EventStatus(str, Enum):
    """Event status enumeration - computed from event dates."""

    UPCOMING = "upcoming"
    ACTIVE = "active"
    PAST = "past"


class PaymentType(str, Enum):
    """Payment type enumeration."""

    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    COMPANY_CARD = "company_card"
    PREPAID = "prepaid"
    INVOICE = "invoice"
    OTHER = "other"


class ExpenseCategory(str, Enum):
    """Expense category enumeration."""

    TRAVEL = "travel"
    ACCOMMODATION = "accommodation"
    MEALS = "meals"
    TRANSPORT = "transport"
    EQUIPMENT = "equipment"
    COMMUNICATION = "communication"
    OTHER = "other"


class ExpenseStatus(str, Enum):
    """Expense status enumeration."""

    PENDING = "pending"
    INCLUDED = "included"
    REIMBURSED = "reimbursed"


class NoteType(str, Enum):
    """Note type enumeration."""

    OBSERVATION = "observation"
    TODO = "todo"
    REPORT_SECTION = "report_section"


class TodoCategory(str, Enum):
    """Todo category enumeration."""

    TRAVEL = "travel"
    ACCOMMODATION = "accommodation"
    PREPARATION = "preparation"
    EQUIPMENT = "equipment"
    CONTACTS = "contacts"
    FOLLOWUP = "followup"
    OTHER = "other"


class IntegrationType(str, Enum):
    """Integration type enumeration."""

    PAPERLESS = "paperless"
    IMMICH = "immich"
    SMTP = "smtp"
    UNSPLASH = "unsplash"


class ContactType(str, Enum):
    """Contact type enumeration for company contacts."""

    BILLING = "billing"
    HR = "hr"
    TECHNICAL = "technical"
    SUPPORT = "support"
    OFFICE = "office"
    SALES = "sales"
    MANAGEMENT = "management"
    OTHER = "other"

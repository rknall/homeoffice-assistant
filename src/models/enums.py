"""Enumeration types for database models."""
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""

    ADMIN = "admin"
    USER = "user"


class CompanyType(str, Enum):
    """Company type enumeration."""

    EMPLOYER = "employer"
    THIRD_PARTY = "third_party"


class EventStatus(str, Enum):
    """Event status enumeration."""

    DRAFT = "draft"
    PREPARATION = "preparation"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class PaymentType(str, Enum):
    """Payment type enumeration."""

    CASH = "cash"
    CREDIT_CARD = "credit_card"
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

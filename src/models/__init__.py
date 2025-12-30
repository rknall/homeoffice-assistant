# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Database models package."""

from src.models.base import Base, TimestampMixin
from src.models.company import Company
from src.models.company_contact import CompanyContact
from src.models.contact import Contact
from src.models.email_template import EmailTemplate
from src.models.enums import (
    CompanyType,
    ContactType,
    EventStatus,
    ExpenseCategory,
    ExpenseStatus,
    IntegrationType,
    NoteType,
    OffsetReference,
    PaymentType,
    TodoCategory,
)
from src.models.event import Event
from src.models.expense import Expense
from src.models.integration_config import IntegrationConfig
from src.models.location_image import LocationImage
from src.models.note import Note
from src.models.permission import Permission
from src.models.photo_reference import PhotoReference
from src.models.plugin_config import PluginConfigModel, PluginMigrationHistory
from src.models.role import Role
from src.models.role_permission import RolePermission
from src.models.session import Session
from src.models.system_settings import SystemSettings
from src.models.todo import Todo
from src.models.todo_template import TodoTemplate
from src.models.user import User
from src.models.user_role import UserRole

__all__ = [
    "Base",
    "Company",
    "CompanyContact",
    "CompanyType",
    "Contact",
    "ContactType",
    "EmailTemplate",
    "Event",
    "EventStatus",
    "Expense",
    "ExpenseCategory",
    "ExpenseStatus",
    "IntegrationConfig",
    "IntegrationType",
    "LocationImage",
    "Note",
    "NoteType",
    "OffsetReference",
    "PaymentType",
    "Permission",
    "PhotoReference",
    "PluginConfigModel",
    "PluginMigrationHistory",
    "Role",
    "RolePermission",
    "Session",
    "SystemSettings",
    "TimestampMixin",
    "Todo",
    "TodoCategory",
    "TodoTemplate",
    "User",
    "UserRole",
]

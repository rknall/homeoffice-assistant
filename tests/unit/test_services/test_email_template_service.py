# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for email_template_service."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from src.models import Company, CompanyContact
from src.models.enums import CompanyType, ContactType, ExpenseCategory, PaymentType
from src.schemas.email_template import EmailTemplateCreate, EmailTemplateUpdate
from src.services import email_template_service


def create_company(db_session, name: str = "Acme") -> Company:
    company = Company(name=name, type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def create_template(
    db_session, company_id: str | None = None, is_default: bool = False, name: str = "Template"
):
    data = EmailTemplateCreate(
        name=name,
        reason="expense_report",
        subject="Subject {{event.name}}",
        body_html="<p>{{company.name}}</p>",
        body_text="Hello {{sender.name}}",
        is_default=is_default,
        company_id=company_id,
        contact_types=[ContactType.BILLING],
    )
    return email_template_service.create_template(db_session, data)


def test_create_template_unsets_other_defaults(db_session):
    first = create_template(db_session, is_default=True, name="First")
    second = create_template(db_session, is_default=True, name="Second")

    db_session.refresh(first)
    assert first.is_default is False
    assert second.is_default is True


def test_get_templates_and_filters(db_session):
    company = create_company(db_session)
    global_template = create_template(db_session, is_default=True, name="Global")
    company_template = create_template(
        db_session, company_id=company.id, is_default=False, name="Company"
    )

    all_templates = email_template_service.get_templates(db_session)
    assert len(all_templates) == 2

    filtered = email_template_service.get_templates(db_session, reason="expense_report")
    assert len(filtered) == 2

    company_filtered = email_template_service.get_templates(
        db_session, company_id=company.id
    )
    assert len(company_filtered) == 2  # company + global

    global_only = email_template_service.get_global_templates(db_session, reason="expense_report")
    assert global_template in global_only
    assert company_template not in global_only

    for_company = email_template_service.get_templates_for_company(
        db_session, company.id, "expense_report"
    )
    assert for_company[0].company_id == company.id


def test_get_default_template_prioritizes_company_specific(db_session):
    company = create_company(db_session)
    global_template = create_template(db_session, is_default=True, name="Global")
    company_template = create_template(
        db_session, company_id=company.id, is_default=True, name="Company"
    )

    assert (
        email_template_service.get_default_template(
            db_session, company.id, "expense_report"
        )
        == company_template
    )
    assert (
        email_template_service.get_default_template(
            db_session, None, "expense_report"
        )
        == global_template
    )


def test_update_and_delete_template(db_session):
    template = create_template(db_session, is_default=False)
    other = create_template(db_session, is_default=True, name="Other")

    updated = email_template_service.update_template(
        db_session,
        template,
        EmailTemplateUpdate(
            name="Updated",
            subject="Updated subject",
            body_html="<p>Updated</p>",
            body_text="Updated text",
            is_default=True,
            contact_types=[ContactType.SUPPORT],
        ),
    )

    assert updated.name == "Updated"
    assert ContactType.SUPPORT.value in updated.contact_types
    db_session.refresh(other)
    assert other.is_default is False

    email_template_service.delete_template(db_session, updated)
    assert email_template_service.get_template(db_session, updated.id) is None


def test_count_globals_and_is_last(db_session):
    template = create_template(db_session, is_default=True)
    assert email_template_service.count_global_templates(db_session) == 1
    assert email_template_service.is_last_global_template(db_session, template) is True

    another = create_template(db_session, is_default=False)
    assert email_template_service.is_last_global_template(db_session, another) is False


def test_reason_helpers():
    reasons = email_template_service.get_reasons()
    assert any(r.reason == "expense_report" for r in reasons)
    info = email_template_service.get_reason_variables("expense_report")
    assert info is not None
    assert email_template_service.get_reason_variables("missing") is None


def test_default_template_content_helper():
    assert email_template_service.get_default_template_content("expense_report") is not None
    assert email_template_service.get_default_template_content("other") is None


def test_render_template_substitution(db_session):
    template = create_template(db_session, is_default=False)
    context = {
        "event": {"name": "Expo"},
        "company": {"name": "Acme"},
        "sender": {"name": "John"},
    }
    subject, body_html, body_text = email_template_service.render_template(
        template, context
    )
    assert "Expo" in subject
    assert "Acme" in body_html
    assert "John" in body_text
    assert "{{" in email_template_service._substitute_variables("{{missing}}", context)


def test_build_expense_report_context():
    event = SimpleNamespace(
        name="Expo",
        start_date=date(2025, 5, 1),
        end_date=date(2025, 5, 5),
        description="Desc",
    )
    contact = SimpleNamespace(name="Main", is_main_contact=True)
    company = SimpleNamespace(name="Acme", contacts=[contact])
    expenses = [
        SimpleNamespace(amount=Decimal("10.00"), currency="EUR"),
        SimpleNamespace(amount=Decimal("5.50"), currency="EUR"),
    ]
    user = SimpleNamespace(username="john", email="john@example.com")

    context = email_template_service.build_expense_report_context(
        event, company, expenses, user
    )

    assert context["event"]["name"] == "Expo"
    assert context["expense"]["total_amount"].startswith("15.50")
    assert context["company"]["recipient_name"] == "Main"


def test_get_sample_context_returns_defaults():
    context = email_template_service.get_sample_context("expense_report")
    assert context["event"]["name"] == "SPS 2025"
    assert email_template_service.get_sample_context("other") == {}


def test_ensure_default_template_exists(db_session):
    first = email_template_service.ensure_default_template_exists(db_session)
    second = email_template_service.ensure_default_template_exists(db_session)
    assert first.id == second.id


def test_contact_type_helpers(db_session):
    template = create_template(db_session, is_default=False)
    contact_types = email_template_service.get_template_contact_types(template)
    assert ContactType.BILLING in contact_types

    response_dict = email_template_service.template_to_response_dict(template)
    assert response_dict["contact_types"][0] == ContactType.BILLING


def test_validate_template_contacts(db_session):
    company = create_company(db_session)
    contact = CompanyContact(
        company_id=company.id,
        name="Billing",
        email="billing@example.com",
        contact_types='["billing"]',
        is_main_contact=True,
    )
    db_session.add(contact)
    db_session.commit()

    template = create_template(db_session, company_id=company.id, is_default=False)

    valid, missing, available = email_template_service.validate_template_contacts(
        db_session, template, company.id
    )
    assert valid is True
    assert missing == []
    assert len(available) == 1

    template.contact_types = '["support"]'
    db_session.commit()

    valid, missing, available = email_template_service.validate_template_contacts(
        db_session, template, company.id
    )
    assert valid is False
    assert missing == [ContactType.SUPPORT]

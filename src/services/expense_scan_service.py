# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense document scanning via LLM extraction."""

import datetime
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from src.models.enums import ExpenseCategory, PaymentType
from src.schemas.expense import ExpenseScanResult

logger = logging.getLogger(__name__)


def validate_extraction(raw: dict[str, Any]) -> ExpenseScanResult:
    """Validate a raw LLM extraction into an ExpenseScanResult.

    Invalid values are dropped to None with a warning instead of failing,
    so a partially usable extraction still helps the user.
    """
    warnings: list[str] = []

    def drop(field: str, value: Any, reason: str) -> None:
        warnings.append(f"{field}: ignored {value!r} ({reason})")

    date_value: datetime.date | None = None
    if raw.get("date") is not None:
        try:
            date_value = datetime.date.fromisoformat(str(raw["date"]))
        except ValueError:
            drop("date", raw["date"], "not an ISO date")

    amount: Decimal | None = None
    if raw.get("amount") is not None:
        try:
            amount = round(Decimal(str(raw["amount"])), 2)
            if amount <= 0:
                drop("amount", raw["amount"], "not positive")
                amount = None
        except InvalidOperation:
            drop("amount", raw["amount"], "not a number")

    currency: str | None = None
    if raw.get("currency") is not None:
        candidate = str(raw["currency"]).strip().upper()
        if len(candidate) == 3 and candidate.isalpha():
            currency = candidate
        else:
            drop("currency", raw["currency"], "not a 3-letter code")

    category: ExpenseCategory | None = None
    if raw.get("category") is not None:
        try:
            category = ExpenseCategory(str(raw["category"]).lower())
        except ValueError:
            drop("category", raw["category"], "unknown category")

    payment_type: PaymentType | None = None
    if raw.get("payment_type") is not None:
        try:
            payment_type = PaymentType(str(raw["payment_type"]).lower())
        except ValueError:
            drop("payment_type", raw["payment_type"], "unknown payment type")

    description: str | None = None
    if raw.get("description"):
        description = str(raw["description"]).strip()[:500] or None

    determined = [date_value, amount, currency, category, payment_type, description]
    if all(v is None for v in determined):
        warnings.append("no expense data could be determined from the document")

    return ExpenseScanResult(
        date=date_value,
        amount=amount,
        currency=currency,
        category=category,
        payment_type=payment_type,
        description=description,
        warnings=warnings,
    )

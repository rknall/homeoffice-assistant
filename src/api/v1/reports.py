# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Report API endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, require_event_permission
from src.api.v1._http import content_disposition
from src.database import get_db
from src.models import Event, User
from src.schemas.expense import SubmissionMethod
from src.schemas.report import (
    GenerateReportRequest,
    ReportPreviewResponse,
    SendReportRequest,
    SendReportResponse,
)
from src.services import (
    report_service,
    submission_service,
    todo_service,
)
from src.services.report_generator import create_report_generator
from src.utils.time import utc_now

router = APIRouter()


@router.get("/{event_id}/expense-report/preview", response_model=ReportPreviewResponse)
async def preview_expense_report(
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.view")),
) -> ReportPreviewResponse:
    """Get a preview of the expense report without generating files."""
    generator = await create_report_generator(db, event)
    try:
        return ReportPreviewResponse(**await generator.get_preview(event))
    finally:
        if generator.paperless:
            await generator.paperless.close()


@router.post("/{event_id}/expense-report/generate")
async def generate_expense_report(
    data: GenerateReportRequest | None = None,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.manage")),
) -> Response:
    """Generate and download expense report as ZIP file.

    Optionally accepts a request body to specify which expenses to include
    and whether to mark them as submitted.
    """
    # Use defaults if no request body provided
    expense_ids = data.expense_ids if data else None
    mark_as_submitted = data.mark_as_submitted if data else True
    submission_method = data.submission_method if data else SubmissionMethod.DOWNLOAD
    notes = data.notes if data else None
    include_private = data.include_private if data else False

    generator = await create_report_generator(db, event)
    try:
        zip_bytes, included_expenses = await generator.generate(
            event, expense_ids, include_private=include_private
        )
        filename = generator.get_filename(event)

        # Create submission record if marking as submitted
        if mark_as_submitted and included_expenses:
            included_ids = [e.id for e in included_expenses]
            submission_service.create_submission(
                db,
                event.id,
                included_ids,
                submission_method,
                notes,
                mark_as_submitted=True,
            )

        # Mark report as sent/exported
        event.report_sent_at = utc_now()
        db.commit()

        # Auto-complete report-related todos
        todo_service.auto_complete_report_todos(db, event.id)

        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": content_disposition(filename),
            },
        )
    finally:
        if generator.paperless:
            await generator.paperless.close()


@router.post("/{event_id}/expense-report/send", response_model=SendReportResponse)
async def send_expense_report(
    data: SendReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    event: Event = Depends(require_event_permission("expense.manage")),
) -> SendReportResponse:
    """Generate and send expense report via email.

    Recipient selection:
    1. If recipient_emails is provided, use those
    2. If auto_select_contacts is True and template has contact_types, use matches
    3. Fall back to company's main contact if available
    """
    return await report_service.send_report(db, event, current_user, data)

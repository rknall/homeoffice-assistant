"""Report API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.services import event_service
from src.services.report_generator import ExpenseReportGenerator, create_report_generator

router = APIRouter()


@router.get("/{event_id}/expense-report/preview")
async def preview_expense_report(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get a preview of the expense report without generating files."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    generator = await create_report_generator(db, event)
    try:
        return generator.get_preview(event)
    finally:
        if generator.paperless:
            await generator.paperless.close()


@router.post("/{event_id}/expense-report/generate")
async def generate_expense_report(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Generate and download expense report as ZIP file."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    generator = await create_report_generator(db, event)
    try:
        zip_bytes = await generator.generate(event)
        filename = generator.get_filename(event)

        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    finally:
        if generator.paperless:
            await generator.paperless.close()

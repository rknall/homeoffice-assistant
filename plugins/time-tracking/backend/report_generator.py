# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""PDF report generator for time tracking timesheets."""

from datetime import date, datetime
from io import BytesIO
from typing import TYPE_CHECKING
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from .models import TimeRecord


class TimesheetReportGenerator:
    """Generates PDF timesheet reports."""

    def __init__(
        self,
        db: Session,
        user_name: str,
        company_name: str,
        period_start: date,
        period_end: date,
    ) -> None:
        """Initialize the report generator.

        Args:
            db: Database session
            user_name: Name of the employee
            company_name: Name of the company
            period_start: Start date of the reporting period
            period_end: End date of the reporting period
        """
        self.db = db
        self.user_name = user_name
        self.company_name = company_name
        self.period_start = period_start
        self.period_end = period_end
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self) -> None:
        """Set up custom paragraph styles."""
        self.styles.add(
            ParagraphStyle(
                "Title",
                parent=self.styles["Heading1"],
                fontSize=16,
                spaceAfter=12,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "Subtitle",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.grey,
                spaceAfter=20,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=12,
                spaceBefore=15,
                spaceAfter=8,
            )
        )

    def generate(self, records: list[TimeRecord]) -> bytes:
        """Generate a PDF timesheet report.

        Args:
            records: List of time records to include in the report

        Returns:
            PDF file content as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements = []

        # Header
        elements.append(self._create_header())
        elements.append(Spacer(1, 10 * mm))

        # Summary section
        elements.append(self._create_summary(records))
        elements.append(Spacer(1, 10 * mm))

        # Time records table
        elements.append(self._create_records_table(records))
        elements.append(Spacer(1, 15 * mm))

        # Signature section
        elements.append(self._create_signature_section())

        doc.build(elements)
        return buffer.getvalue()

    def _create_header(self) -> Table:
        """Create the report header with company and employee info."""
        period_str = (
            f"{self.period_start.strftime('%d.%m.%Y')} - "
            f"{self.period_end.strftime('%d.%m.%Y')}"
        )

        header_data = [
            [
                Paragraph("Timesheet / Stundennachweis", self.styles["Title"]),
                "",
            ],
            [
                Paragraph(f"Employee: {self.user_name}", self.styles["Normal"]),
                Paragraph(f"Company: {self.company_name}", self.styles["Normal"]),
            ],
            [
                Paragraph(f"Period: {period_str}", self.styles["Normal"]),
                Paragraph(
                    f"Generated: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                    self.styles["Normal"],
                ),
            ],
        ]

        table = Table(header_data, colWidths=[9 * cm, 8 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, 0), (1, 0)),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    def _create_summary(self, records: list[TimeRecord]) -> Table:
        """Create a summary table with totals."""
        total_gross = sum(r.gross_hours or 0 for r in records)
        total_net = sum(r.net_hours or 0 for r in records)
        total_breaks = sum(r.break_minutes or 0 for r in records)
        work_days = sum(
            1 for r in records if r.day_type in ("work", "doctor_visit")
        )
        vacation_days = sum(1 for r in records if r.day_type == "vacation")
        sick_days = sum(1 for r in records if r.day_type == "sick")
        holiday_days = sum(1 for r in records if r.day_type == "public_holiday")

        summary_data = [
            ["Summary / Zusammenfassung", "", "", ""],
            ["Work Days", str(work_days), "Net Hours", f"{total_net:.1f}h"],
            ["Vacation", str(vacation_days), "Gross Hours", f"{total_gross:.1f}h"],
            ["Sick Days", str(sick_days), "Total Breaks", f"{total_breaks} min"],
            ["Public Holidays", str(holiday_days), "", ""],
        ]

        table = Table(summary_data, colWidths=[4 * cm, 3 * cm, 4 * cm, 3 * cm])
        table.setStyle(
            TableStyle(
                [
                    # Header row
                    ("SPAN", (0, 0), (3, 0)),
                    ("BACKGROUND", (0, 0), (3, 0), colors.Color(0.9, 0.9, 0.9)),
                    ("FONTNAME", (0, 0), (3, 0), "Helvetica-Bold"),
                    # All cells
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                    # Label columns
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 1), (2, -1), "Helvetica-Bold"),
                ]
            )
        )
        return table

    def _create_records_table(self, records: list[TimeRecord]) -> Table:
        """Create the main time records table."""
        # Sort by date
        sorted_records = sorted(records, key=lambda r: r.date)

        # Table header
        table_data = [
            ["Date", "Day", "Type", "Check In", "Check Out", "Break", "Net Hours"],
        ]

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_type_labels = {
            "work": "Work",
            "vacation": "Vacation",
            "sick": "Sick",
            "doctor_visit": "Doctor",
            "public_holiday": "Holiday",
            "comp_time": "Comp Time",
            "unpaid_leave": "Unpaid",
            "weekend": "Weekend",
        }

        for record in sorted_records:
            weekday = day_names[record.date.weekday()]
            day_type = day_type_labels.get(record.day_type, record.day_type)
            check_in = record.check_in.strftime("%H:%M") if record.check_in else "-"
            check_out = (
                record.check_out.strftime("%H:%M") if record.check_out else "-"
            )
            break_min = f"{record.break_minutes}" if record.break_minutes else "-"
            net_hours = f"{record.net_hours:.1f}" if record.net_hours else "-"

            table_data.append(
                [
                    record.date.strftime("%d.%m"),
                    weekday,
                    day_type,
                    check_in,
                    check_out,
                    break_min,
                    net_hours,
                ]
            )

        # Add totals row
        total_net = sum(r.net_hours or 0 for r in records)
        table_data.append(
            ["", "", "", "", "", "Total:", f"{total_net:.1f}h"]
        )

        col_widths = [2 * cm, 1.5 * cm, 2.5 * cm, 2 * cm, 2 * cm, 1.5 * cm, 2 * cm]
        table = Table(table_data, colWidths=col_widths)

        style_commands = [
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.6)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            # All cells
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (3, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("PADDING", (0, 0), (-1, -1), 4),
            # Totals row
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ]

        # Alternate row colors
        for i in range(1, len(table_data) - 1):
            if i % 2 == 0:
                style_commands.append(
                    ("BACKGROUND", (0, i), (-1, i), colors.Color(0.97, 0.97, 0.97))
                )

        table.setStyle(TableStyle(style_commands))
        return table

    def _create_signature_section(self) -> Table:
        """Create the signature section."""
        signature_data = [
            ["", ""],
            ["_" * 30, "_" * 30],
            ["Employee Signature", "Supervisor Signature"],
            ["Date: _______________", "Date: _______________"],
        ]

        table = Table(signature_data, colWidths=[8 * cm, 8 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, 0), 30),
                    ("FONTSIZE", (0, 2), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 2), (-1, 2), colors.grey),
                ]
            )
        )
        return table


def generate_monthly_timesheet(
    db: Session,
    user_id: UUID,
    company_id: UUID,
    year: int,
    month: int,
) -> bytes:
    """Generate a monthly timesheet PDF.

    Args:
        db: Database session
        user_id: User ID
        company_id: Company ID
        year: Year
        month: Month (1-12)

    Returns:
        PDF file content as bytes
    """
    from calendar import monthrange

    from .models import TimeRecord

    # Get period dates
    _, last_day = monthrange(year, month)
    period_start = date(year, month, 1)
    period_end = date(year, month, last_day)

    # Fetch records
    records = (
        db.query(TimeRecord)
        .filter(
            TimeRecord.user_id == user_id,
            TimeRecord.company_id == company_id,
            TimeRecord.date >= period_start,
            TimeRecord.date <= period_end,
        )
        .order_by(TimeRecord.date)
        .all()
    )

    # Get user and company names (simplified - would use actual models)
    from src.models import Company, User

    user = db.query(User).filter(User.id == user_id).first()
    company = db.query(Company).filter(Company.id == company_id).first()

    user_name = user.full_name or user.username if user else "Unknown"
    company_name = company.name if company else "Unknown"

    generator = TimesheetReportGenerator(
        db=db,
        user_name=user_name,
        company_name=company_name,
        period_start=period_start,
        period_end=period_end,
    )

    return generator.generate(records)

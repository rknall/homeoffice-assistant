# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company API endpoints."""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.api.deps import require_permission
from src.database import get_db
from src.models import User
from src.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
    LogoUploadResponse,
)
from src.services import company_service, file_storage_service, rbac_service

router = APIRouter()

# Reads need company.view and writes company.manage, both scoped to the
# company in the path. Creating a company has no company scope yet, so it
# needs company.manage from a global role.
view_company = require_permission("company.view", company_id_param="company_id")
manage_company = require_permission("company.manage", company_id_param="company_id")
create_company_permission = require_permission("company.manage")


@router.get("", response_model=list[CompanyResponse])
def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(view_company),
) -> list[CompanyResponse]:
    """List the companies the user may view."""
    allowed = rbac_service.companies_with_permission(db, current_user, "company.view")
    companies = [
        c
        for c in company_service.get_companies(db)
        if allowed is None or c.id in allowed
    ]
    return [
        CompanyResponse(**company_service.company_to_response_dict(c))
        for c in companies
    ]


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(create_company_permission),
) -> CompanyResponse:
    """Create a new company."""
    existing = company_service.get_company_by_name(db, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company with this name already exists",
        )

    company = company_service.create_company(db, data)
    return CompanyResponse(**company_service.company_to_response_dict(company))


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(view_company),
) -> CompanyResponse:
    """Get a company by ID."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return CompanyResponse(**company_service.company_to_response_dict(company))


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: uuid.UUID,
    data: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(manage_company),
) -> CompanyResponse:
    """Update a company."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    if data.name and data.name != company.name:
        existing = company_service.get_company_by_name(db, data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company with this name already exists",
            )

    company = company_service.update_company(db, company, data)
    return CompanyResponse(**company_service.company_to_response_dict(company))


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(manage_company),
) -> None:
    """Delete a company."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    logo_path = company.logo_path
    company_service.delete_company(db, company)
    file_storage_service.remove_logo(logo_path)


@router.post("/{company_id}/logo", response_model=LogoUploadResponse)
async def upload_company_logo(
    company_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(manage_company),
) -> LogoUploadResponse:
    """Upload a logo for a company.

    Stores the logo locally and updates the company's logo_path field.
    """
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    content = await file.read()
    try:
        logo_path = file_storage_service.save_logo(
            company_id, file.filename, content, company.logo_path
        )
    except file_storage_service.FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    company.logo_path = logo_path
    db.commit()

    return LogoUploadResponse(message="Logo uploaded successfully", logo_path=logo_path)


@router.delete("/{company_id}/logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_logo(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(manage_company),
) -> None:
    """Delete a company's logo."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    if company.logo_path:
        file_storage_service.remove_logo(company.logo_path)
        company.logo_path = None
        db.commit()


@router.get("/{company_id}/logo")
def get_company_logo(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(view_company),
) -> FileResponse:
    """Get a company's logo file."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    if not company.logo_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logo uploaded for this company",
        )

    found = file_storage_service.logo_file(company.logo_path)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Logo file not found",
        )
    logo_path, media_type = found
    return FileResponse(
        logo_path, media_type=media_type, headers=file_storage_service.LOGO_HEADERS
    )

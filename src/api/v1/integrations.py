"""Integration API endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_admin, get_current_user, get_db
from src.integrations.base import DocumentProvider
from src.models import User
from src.models.enums import IntegrationType
from src.schemas.integration import (
    IntegrationConfigCreate,
    IntegrationConfigResponse,
    IntegrationConfigUpdate,
    IntegrationTestResult,
    IntegrationTypeInfo,
    StoragePathResponse,
    TagResponse,
)
from src.services import integration_service

router = APIRouter()


@router.get("/types", response_model=list[IntegrationTypeInfo])
def list_integration_types(
    current_user: User = Depends(get_current_user),
) -> list[IntegrationTypeInfo]:
    """List all available integration types with their config schemas."""
    types = integration_service.list_integration_types()
    return [IntegrationTypeInfo(**t) for t in types]


@router.get("", response_model=list[IntegrationConfigResponse])
def list_integrations(
    integration_type: Optional[IntegrationType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IntegrationConfigResponse]:
    """List all configured integrations."""
    configs = integration_service.get_integration_configs(db, integration_type)
    return [IntegrationConfigResponse.model_validate(c) for c in configs]


@router.post("", response_model=IntegrationConfigResponse, status_code=status.HTTP_201_CREATED)
def create_integration(
    data: IntegrationConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> IntegrationConfigResponse:
    """Create a new integration configuration. Admin only."""
    config = integration_service.create_integration_config(db, data, current_user.id)
    return IntegrationConfigResponse.model_validate(config)


@router.get("/{config_id}", response_model=IntegrationConfigResponse)
def get_integration(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationConfigResponse:
    """Get a single integration configuration."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    return IntegrationConfigResponse.model_validate(config)


@router.put("/{config_id}", response_model=IntegrationConfigResponse)
def update_integration(
    config_id: str,
    data: IntegrationConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> IntegrationConfigResponse:
    """Update an integration configuration. Admin only."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    config = integration_service.update_integration_config(db, config, data)
    return IntegrationConfigResponse.model_validate(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> None:
    """Delete an integration configuration. Admin only."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    integration_service.delete_integration_config(db, config)


@router.post("/{config_id}/test", response_model=IntegrationTestResult)
async def test_integration(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationTestResult:
    """Test connectivity for an integration."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    success, message = await integration_service.test_integration_connection(config)
    return IntegrationTestResult(success=success, message=message)


@router.get("/{config_id}/storage-paths", response_model=list[StoragePathResponse])
async def list_storage_paths(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StoragePathResponse]:
    """List storage paths from a Paperless integration."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    if config.integration_type != IntegrationType.PAPERLESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only available for Paperless integrations",
        )

    provider = integration_service.create_provider_instance(config)
    if not provider or not isinstance(provider, DocumentProvider):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create provider instance",
        )

    try:
        paths = await provider.list_storage_paths()
        return [StoragePathResponse(**p) for p in paths]
    finally:
        await provider.close()


@router.get("/{config_id}/tags", response_model=list[TagResponse])
async def list_tags(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TagResponse]:
    """List tags from a Paperless integration."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    if config.integration_type != IntegrationType.PAPERLESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only available for Paperless integrations",
        )

    provider = integration_service.create_provider_instance(config)
    if not provider or not isinstance(provider, DocumentProvider):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create provider instance",
        )

    try:
        tags = await provider.list_tags()
        return [TagResponse(**t) for t in tags]
    finally:
        await provider.close()

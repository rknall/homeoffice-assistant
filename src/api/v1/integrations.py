# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integration API endpoints."""

import logging
import smtplib
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, require_permission
from src.api.provider_errors import provider_errors
from src.database import get_db
from src.integrations.base import LlmProvider
from src.integrations.failure import failure_category
from src.integrations.llm import LlmError
from src.integrations.registry import IntegrationRegistry
from src.models import User
from src.models.enums import IntegrationType
from src.schemas.integration import (
    EventCustomFieldChoicesResponse,
    IntegrationConfigCreate,
    IntegrationConfigDetailResponse,
    IntegrationConfigResponse,
    IntegrationConfigUpdate,
    IntegrationTestResult,
    IntegrationTypeInfo,
    LlmModelsRequest,
    StoragePathResponse,
    TestEmailRequest,
    TestEmailResponse,
    UnsplashDownloadResponse,
    UnsplashSearchResponse,
)
from src.services import integration_service
from src.services.integration_service import ProviderError

router = APIRouter()
logger = logging.getLogger(__name__)

# Integrations are system-wide, so both checks use global roles only.
# integration.use covers reading the configured integrations and calling a
# provider; integration.config covers creating, editing and deleting them.
use_integrations = require_permission("integration.use")
configure_integrations = require_permission("integration.config")


@router.get(
    "/event-custom-field-choices", response_model=EventCustomFieldChoicesResponse
)
async def get_event_custom_field_choices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventCustomFieldChoicesResponse:
    """Get available choices for the event custom field from Paperless.

    The event pages need these choices, so any logged-in user may read them;
    the response holds only the field name and its choice labels.
    """
    unavailable = EventCustomFieldChoicesResponse(
        available=False, custom_field_name="", choices=[]
    )
    config = integration_service.get_active_document_provider(db)
    if config is None:
        return unavailable
    custom_field_name = integration_service.get_decrypted_config(config).get(
        "custom_field_name", "Trip"
    )
    try:
        async with integration_service.open_provider(
            db, config.id, IntegrationType.PAPERLESS
        ) as provider:
            custom_field = await provider.get_custom_field_by_name(custom_field_name)
            if not custom_field:
                return EventCustomFieldChoicesResponse(
                    available=False,
                    custom_field_name=custom_field_name,
                    choices=[],
                )
            choices = await provider.get_custom_field_choices_with_values(
                custom_field["id"]
            )
            return EventCustomFieldChoicesResponse(
                available=True,
                custom_field_name=custom_field_name,
                choices=sorted(choices, key=lambda c: c["label"]),
            )
    except ProviderError:
        return unavailable


@router.get("/types", response_model=list[IntegrationTypeInfo])
def list_integration_types(
    current_user: User = Depends(use_integrations),
) -> list[IntegrationTypeInfo]:
    """List all available integration types with their config schemas."""
    types = integration_service.list_integration_types()
    return [IntegrationTypeInfo(**t) for t in types]


@router.post("/llm/models", response_model=list[str])
async def list_llm_models(
    data: LlmModelsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(configure_integrations),
) -> list[str]:
    """List the models an OpenAI-compatible LLM endpoint offers."""
    config = integration_service.resolve_llm_models_config(db, data)
    provider = IntegrationRegistry.create_provider(IntegrationType.LLM.value, config)
    if not isinstance(provider, LlmProvider):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create provider instance",
        )
    try:
        return await provider.list_models()
    except LlmError as e:
        logger.error("Could not list LLM models: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not list models: {failure_category(e)}",
        ) from e
    finally:
        await provider.close()


@router.get("", response_model=list[IntegrationConfigResponse])
def list_integrations(
    integration_type: IntegrationType | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(use_integrations),
) -> list[IntegrationConfigResponse]:
    """List all configured integrations."""
    configs = integration_service.get_integration_configs(db, integration_type)
    return [IntegrationConfigResponse.model_validate(c) for c in configs]


@router.post(
    "", response_model=IntegrationConfigResponse, status_code=status.HTTP_201_CREATED
)
def create_integration(
    data: IntegrationConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(configure_integrations),
) -> IntegrationConfigResponse:
    """Create a new integration configuration."""
    config = integration_service.create_integration_config(db, data, current_user.id)
    return IntegrationConfigResponse.model_validate(config)


@router.get("/{config_id}", response_model=IntegrationConfigResponse)
def get_integration(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(use_integrations),
) -> IntegrationConfigResponse:
    """Get a single integration configuration."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    return IntegrationConfigResponse.model_validate(config)


@router.get("/{config_id}/config", response_model=IntegrationConfigDetailResponse)
def get_integration_config_detail(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(configure_integrations),
) -> IntegrationConfigDetailResponse:
    """Get integration configuration with masked secrets for editing."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    masked_config = integration_service.get_masked_config(config)
    return IntegrationConfigDetailResponse(
        id=config.id,
        integration_type=config.integration_type,
        name=config.name,
        is_active=config.is_active,
        created_by=config.created_by,
        created_at=config.created_at,
        updated_at=config.updated_at,
        config=masked_config,
        secrets_set=integration_service.get_secrets_set(config),
    )


@router.put("/{config_id}", response_model=IntegrationConfigResponse)
def update_integration(
    config_id: uuid.UUID,
    data: IntegrationConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(configure_integrations),
) -> IntegrationConfigResponse:
    """Update an integration configuration."""
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
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(configure_integrations),
) -> None:
    """Delete an integration configuration."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    integration_service.delete_integration_config(db, config)


@router.post("/{config_id}/test", response_model=IntegrationTestResult)
async def test_integration(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(use_integrations),
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


@router.post("/{config_id}/test-email", response_model=TestEmailResponse)
async def send_test_email(
    config_id: uuid.UUID,
    data: TestEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(use_integrations),
) -> TestEmailResponse:
    """Send a test email via an SMTP integration."""
    with provider_errors():
        async with integration_service.open_provider(
            db, config_id, IntegrationType.SMTP
        ) as provider:
            try:
                success = await provider.send_email(
                    to=[data.to_email],
                    subject="Test Email from HomeOffice Assistant",
                    body=(
                        "This is a test email from HomeOffice Assistant.\n\n"
                        "If you received this, your SMTP configuration is working."
                    ),
                )
            except (smtplib.SMTPException, OSError, ValueError) as e:
                logger.error("Test email failed: %s", e)
                return TestEmailResponse(
                    success=False,
                    message=f"Failed to send test email: {failure_category(e)}",
                )
    if success:
        return TestEmailResponse(success=True, message="Test email sent successfully")
    return TestEmailResponse(success=False, message="Failed to send test email")


@router.get("/{config_id}/storage-paths", response_model=list[StoragePathResponse])
async def list_storage_paths(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(use_integrations),
) -> list[StoragePathResponse]:
    """List storage paths from a Paperless integration."""
    with provider_errors():
        async with integration_service.open_provider(
            db, config_id, IntegrationType.PAPERLESS
        ) as provider:
            paths = await provider.list_storage_paths()
    return [StoragePathResponse(**p) for p in paths]


@router.get("/{config_id}/unsplash/search", response_model=UnsplashSearchResponse)
async def search_unsplash_images(
    config_id: uuid.UUID,
    query: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(use_integrations),
) -> UnsplashSearchResponse:
    """Search for images on Unsplash."""
    with provider_errors():
        async with integration_service.open_provider(
            db, config_id, IntegrationType.UNSPLASH
        ) as provider:
            result = await provider.search_images(query, page=page, per_page=per_page)
    return UnsplashSearchResponse(**result)


@router.post(
    "/{config_id}/unsplash/download/{image_id}",
    response_model=UnsplashDownloadResponse,
)
async def trigger_unsplash_download(
    config_id: uuid.UUID,
    image_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(use_integrations),
) -> UnsplashDownloadResponse:
    """Trigger download tracking for an Unsplash image (required by API guidelines)."""
    with provider_errors():
        async with integration_service.open_provider(
            db, config_id, IntegrationType.UNSPLASH
        ) as provider:
            download_url = await provider.trigger_download(image_id)
    return UnsplashDownloadResponse(download_url=download_url)

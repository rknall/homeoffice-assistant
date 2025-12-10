# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_admin, get_current_user, get_db
from src.integrations.base import DocumentProvider, EmailProvider, ImageSearchProvider
from src.models import User
from src.models.enums import IntegrationType
from src.schemas.integration import (
    AddChoiceRequest,
    CustomFieldChoicesResponse,
    CustomFieldResponse,
    EventCustomFieldChoicesResponse,
    IntegrationConfigCreate,
    IntegrationConfigDetailResponse,
    IntegrationConfigResponse,
    IntegrationConfigUpdate,
    IntegrationTestResult,
    IntegrationTypeInfo,
    StoragePathResponse,
    TagResponse,
    TestEmailRequest,
    TestEmailResponse,
    UnsplashSearchResponse,
)
from src.services import integration_service

router = APIRouter()


@router.get(
    "/event-custom-field-choices", response_model=EventCustomFieldChoicesResponse
)
async def get_event_custom_field_choices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventCustomFieldChoicesResponse:
    """Get available choices for the event custom field from Paperless."""
    # Get active Paperless integration
    paperless_config = integration_service.get_active_document_provider(db)
    if not paperless_config:
        return EventCustomFieldChoicesResponse(
            available=False,
            custom_field_name="",
            choices=[],
        )

    provider = integration_service.create_provider_instance(paperless_config)
    if not provider or not isinstance(provider, DocumentProvider):
        return EventCustomFieldChoicesResponse(
            available=False,
            custom_field_name="",
            choices=[],
        )

    try:
        # Get the configured custom field name
        decrypted_config = integration_service.get_decrypted_config(paperless_config)
        custom_field_name = decrypted_config.get("custom_field_name", "Trip")

        # Find the custom field and get its choices
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
        # Sort by label
        choices_sorted = sorted(choices, key=lambda c: c["label"])
        return EventCustomFieldChoicesResponse(
            available=True,
            custom_field_name=custom_field_name,
            choices=choices_sorted,
        )
    finally:
        await provider.close()


@router.get("/types", response_model=list[IntegrationTypeInfo])
def list_integration_types(
    current_user: User = Depends(get_current_user),
) -> list[IntegrationTypeInfo]:
    """List all available integration types with their config schemas."""
    types = integration_service.list_integration_types()
    return [IntegrationTypeInfo(**t) for t in types]


@router.get("", response_model=list[IntegrationConfigResponse])
def list_integrations(
    integration_type: IntegrationType | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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


@router.get("/{config_id}/config", response_model=IntegrationConfigDetailResponse)
def get_integration_config_detail(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> IntegrationConfigDetailResponse:
    """Get integration configuration with masked secrets for editing. Admin only."""
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
    )


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


@router.post("/{config_id}/test-email", response_model=TestEmailResponse)
async def send_test_email(
    config_id: str,
    data: TestEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestEmailResponse:
    """Send a test email via an SMTP integration."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    if config.integration_type != IntegrationType.SMTP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only available for SMTP integrations",
        )

    provider = integration_service.create_provider_instance(config)
    if not provider or not isinstance(provider, EmailProvider):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create provider instance",
        )

    try:
        success = await provider.send_email(
            to=[data.to_email],
            subject="Test Email from HomeOffice Assistant",
            body=(
                "This is a test email from HomeOffice Assistant.\n\n"
                "If you received this, your SMTP configuration is working."
            ),
        )
        if success:
            return TestEmailResponse(
                success=True, message="Test email sent successfully"
            )
        return TestEmailResponse(success=False, message="Failed to send test email")
    except Exception as e:
        return TestEmailResponse(success=False, message=str(e))
    finally:
        await provider.close()


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


@router.get("/{config_id}/custom-fields", response_model=list[CustomFieldResponse])
async def list_custom_fields(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CustomFieldResponse]:
    """List custom fields from a Paperless integration."""
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
        fields = await provider.list_custom_fields()
        return [CustomFieldResponse(**f) for f in fields]
    finally:
        await provider.close()


@router.get("/{config_id}/custom-fields/{field_id}", response_model=CustomFieldResponse)
async def get_custom_field(
    config_id: str,
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomFieldResponse:
    """Get a custom field by ID from a Paperless integration."""
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
        field = await provider.get_custom_field(field_id)
        if not field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom field not found",
            )
        return CustomFieldResponse(**field)
    finally:
        await provider.close()


@router.get(
    "/{config_id}/custom-fields/{field_id}/choices",
    response_model=CustomFieldChoicesResponse,
)
async def get_custom_field_choices(
    config_id: str,
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomFieldChoicesResponse:
    """Get choices for a select-type custom field from a Paperless integration."""
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
        choices = await provider.get_custom_field_choices(field_id)
        return CustomFieldChoicesResponse(choices=choices)
    finally:
        await provider.close()


@router.post(
    "/{config_id}/custom-fields/{field_id}/choices",
    response_model=CustomFieldChoicesResponse,
)
async def add_custom_field_choice(
    config_id: str,
    field_id: int,
    data: AddChoiceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomFieldChoicesResponse:
    """Add a choice to a select-type custom field in a Paperless integration."""
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
        try:
            await provider.add_custom_field_choice(field_id, data.choice)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        # Return updated choices
        choices = await provider.get_custom_field_choices(field_id)
        return CustomFieldChoicesResponse(choices=choices)
    finally:
        await provider.close()


@router.get("/{config_id}/unsplash/search", response_model=UnsplashSearchResponse)
async def search_unsplash_images(
    config_id: str,
    query: str,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnsplashSearchResponse:
    """Search for images on Unsplash."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    if config.integration_type != IntegrationType.UNSPLASH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only available for Unsplash integrations",
        )

    provider = integration_service.create_provider_instance(config)
    if not provider or not isinstance(provider, ImageSearchProvider):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create provider instance",
        )

    try:
        result = await provider.search_images(query, page=page, per_page=per_page)
        return UnsplashSearchResponse(**result)
    finally:
        await provider.close()


@router.post("/{config_id}/unsplash/download/{image_id}")
async def trigger_unsplash_download(
    config_id: str,
    image_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Trigger download tracking for an Unsplash image (required by API guidelines)."""
    config = integration_service.get_integration_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    if config.integration_type != IntegrationType.UNSPLASH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only available for Unsplash integrations",
        )

    provider = integration_service.create_provider_instance(config)
    if not provider or not isinstance(provider, ImageSearchProvider):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create provider instance",
        )

    try:
        download_url = await provider.trigger_download(image_id)
        return {"download_url": download_url}
    finally:
        await provider.close()

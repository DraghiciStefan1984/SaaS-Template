import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from .models import (
    CredentialType,
    IntegrationAccount,
    IntegrationAccountStatus,
    IntegrationCredential,
    IntegrationProvider,
    ProviderAuthType,
    SyncLogStatus,
)


class IntegrationProviderNotConfigured(APIException):
    status_code = 503
    default_detail = (
        "This provider is not configured yet. Add the provider account credentials "
        "or OAuth client settings before enabling this integration."
    )
    default_code = "integration_provider_not_configured"


def _fernet():
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_credential_payload(payload):
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return _fernet().encrypt(serialized.encode()).decode()


def decrypt_credential_payload(encrypted_payload):
    try:
        decrypted = _fernet().decrypt(encrypted_payload.encode()).decode()
    except InvalidToken as exc:
        raise ValidationError("Credential payload could not be decrypted.") from exc
    return json.loads(decrypted)


def provider_health_check(provider):
    # Real health checks are provider-specific and must live in replaceable provider clients.
    if (
        provider.auth_type == ProviderAuthType.OAUTH2
        and not provider.config.get("oauth_client_configured")
    ):
        return {
            "status": "not_configured",
            "detail": "OAuth client settings are not configured for this provider yet.",
        }
    return {"status": "ok", "detail": "Provider registry entry is available."}


@transaction.atomic
def connect_integration_account(
    *,
    organization,
    provider,
    connected_by,
    external_account_id="",
    display_name="",
    scopes=None,
    credential_type=None,
    credential_payload=None,
    metadata=None,
):
    if not provider.is_active:
        raise ValidationError({"provider": "This provider is disabled."})

    if provider.auth_type == ProviderAuthType.OAUTH2 and not credential_payload:
        # Once a real OAuth app exists, exchange authorization codes in a provider client here.
        raise IntegrationProviderNotConfigured()

    if provider.auth_type == ProviderAuthType.API_KEY and not credential_payload:
        raise ValidationError(
            {"credential_payload": "API key providers require a credential payload."}
        )

    account, _created = IntegrationAccount.objects.update_or_create(
        organization=organization,
        provider=provider,
        external_account_id=external_account_id,
        defaults={
            "display_name": display_name or provider.name,
            "status": IntegrationAccountStatus.CONNECTED,
            "scopes": scopes or provider.scopes,
            "connected_by": connected_by,
            "metadata": metadata or {},
        },
    )

    if credential_payload:
        credential = IntegrationCredential.objects.filter(integration_account=account).first()
        encrypted_payload = encrypt_credential_payload(credential_payload)
        if credential:
            credential.credential_type = credential_type or credential.credential_type
            credential.encrypted_payload = encrypted_payload
            credential.save(update_fields=["credential_type", "encrypted_payload", "updated_at"])
        else:
            IntegrationCredential.objects.create(
                integration_account=account,
                credential_type=credential_type or CredentialType.API_KEY,
                encrypted_payload=encrypted_payload,
            )

    return account


@transaction.atomic
def disconnect_integration_account(account):
    account.status = IntegrationAccountStatus.DISCONNECTED
    account.save(update_fields=["status", "updated_at"])
    return account


def create_sync_log(
    *,
    integration_account,
    action,
    status=SyncLogStatus.PENDING,
    error_message="",
    external_request_id="",
    retry_count=0,
    metadata=None,
):
    now = timezone.now()
    completed_at = now if status in {SyncLogStatus.SUCCEEDED, SyncLogStatus.FAILED} else None
    return integration_account.sync_logs.create(
        action=action,
        status=status,
        started_at=now,
        completed_at=completed_at,
        error_message=error_message,
        external_request_id=external_request_id,
        retry_count=retry_count,
        metadata=metadata or {},
    )


def get_provider_by_slug(slug):
    return IntegrationProvider.objects.get(slug=slug, is_active=True)

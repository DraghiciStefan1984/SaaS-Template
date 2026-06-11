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


def provider_is_customer_configurable(provider):
    return provider.config.get("customer_configurable", True) is True


def provider_credential_fields(provider):
    fields = provider.config.get("credential_fields", [])
    if not isinstance(fields, list):
        return []
    return [
        {
            "key": field.get("key", ""),
            "label": field.get("label", ""),
            "secret": bool(field.get("secret", True)),
            "required": bool(field.get("required", True)),
        }
        for field in fields
        if isinstance(field, dict) and field.get("key") and field.get("label")
    ]


def validate_provider_credential_payload(provider, credential_payload):
    if credential_payload is None:
        return credential_payload
    if not isinstance(credential_payload, dict):
        raise ValidationError({"credential_payload": "Expected a JSON object."})

    fields = provider_credential_fields(provider)
    if not fields and provider.auth_type == ProviderAuthType.API_KEY:
        fields = [{"key": "api_key", "required": True}]

    allowed_keys = {field["key"] for field in fields}
    unexpected_keys = sorted(set(credential_payload) - allowed_keys)
    if unexpected_keys:
        raise ValidationError(
            {"credential_payload": f"Unsupported credential fields: {', '.join(unexpected_keys)}."}
        )

    missing_keys = [
        field["key"]
        for field in fields
        if field.get("required") and not credential_payload.get(field["key"])
    ]
    if missing_keys:
        raise ValidationError(
            {"credential_payload": f"Missing credential fields: {', '.join(missing_keys)}."}
        )

    for key, value in credential_payload.items():
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(
                {"credential_payload": f"Credential field '{key}' must be a non-empty string."}
            )
        if len(value) > 8192:
            raise ValidationError(
                {"credential_payload": f"Credential field '{key}' exceeds 8192 characters."}
            )
    return credential_payload


def _fernet():
    digest = hashlib.sha256(settings.INTEGRATION_CREDENTIALS_KEY.encode()).digest()
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


def get_organization_provider_api_key(organization, provider_slug):
    credential = (
        IntegrationCredential.objects.filter(
            integration_account__organization=organization,
            integration_account__provider__slug=provider_slug,
            integration_account__status=IntegrationAccountStatus.CONNECTED,
            credential_type=CredentialType.API_KEY,
        )
        .select_related("integration_account")
        .order_by("-updated_at")
        .first()
    )
    if credential is None:
        return ""
    payload = decrypt_credential_payload(credential.encrypted_payload)
    api_key = payload.get("api_key", "") if isinstance(payload, dict) else ""
    return api_key if isinstance(api_key, str) else ""


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


def _upsert_integration_credential(account, credential_type, credential_payload):
    credential = IntegrationCredential.objects.filter(integration_account=account).first()
    encrypted_payload = encrypt_credential_payload(credential_payload)
    if credential:
        credential.credential_type = credential_type or credential.credential_type
        credential.encrypted_payload = encrypted_payload
        credential.save(update_fields=["credential_type", "encrypted_payload", "updated_at"])
        return credential
    return IntegrationCredential.objects.create(
        integration_account=account,
        credential_type=credential_type or CredentialType.API_KEY,
        encrypted_payload=encrypted_payload,
    )


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
    if not provider_is_customer_configurable(provider):
        raise ValidationError({"provider": "This provider is managed by the SaaS platform."})

    metadata = metadata or {}
    if not isinstance(metadata, dict):
        raise ValidationError({"metadata": "Expected a JSON object."})
    validate_provider_credential_payload(provider, credential_payload)

    if provider.auth_type == ProviderAuthType.OAUTH2:
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
            "metadata": metadata,
        },
    )

    if credential_payload:
        _upsert_integration_credential(account, credential_type, credential_payload)

    return account


@transaction.atomic
def reconnect_integration_account(
    account,
    *,
    connected_by,
    external_account_id="",
    display_name="",
    scopes=None,
    credential_type=None,
    credential_payload=None,
):
    provider = account.provider
    if not provider.is_active:
        raise ValidationError({"provider": "This provider is disabled."})
    if not provider_is_customer_configurable(provider):
        raise ValidationError({"provider": "This provider is managed by the SaaS platform."})
    validate_provider_credential_payload(provider, credential_payload)
    if provider.auth_type == ProviderAuthType.OAUTH2:
        # TODO(oauth): Exchange an authorization code through the provider
        # client after OAuth client ID/secret and redirect URI are configured.
        raise IntegrationProviderNotConfigured()
    if provider.auth_type == ProviderAuthType.API_KEY and not credential_payload:
        raise ValidationError(
            {"credential_payload": "API key providers require a credential payload."}
        )

    account.status = IntegrationAccountStatus.CONNECTED
    account.connected_by = connected_by
    account.external_account_id = external_account_id or account.external_account_id
    account.display_name = display_name or account.display_name or provider.name
    account.scopes = scopes if scopes is not None else account.scopes
    metadata = account.metadata if isinstance(account.metadata, dict) else {}
    account.metadata = {
        key: value for key, value in metadata.items() if key != "credential_deleted"
    }
    account.save(
        update_fields=[
            "status",
            "connected_by",
            "external_account_id",
            "display_name",
            "scopes",
            "metadata",
            "updated_at",
        ]
    )
    if credential_payload:
        _upsert_integration_credential(account, credential_type, credential_payload)
    create_sync_log(
        integration_account=account,
        action="reconnect",
        status=SyncLogStatus.SUCCEEDED,
        metadata={"provider_slug": provider.slug},
    )
    return account


@transaction.atomic
def disconnect_integration_account(account):
    IntegrationCredential.objects.filter(integration_account=account).delete()
    account.status = IntegrationAccountStatus.DISCONNECTED
    account.external_account_id = ""
    account.scopes = []
    metadata = account.metadata if isinstance(account.metadata, dict) else {}
    account.metadata = {**metadata, "credential_deleted": True}
    account.save(
        update_fields=[
            "status",
            "external_account_id",
            "scopes",
            "metadata",
            "updated_at",
        ]
    )
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

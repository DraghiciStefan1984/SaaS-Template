import pytest
from django.test import override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.ai.models import (
    AICallLog,
    AICallStatus,
    AIExecutionStrategy,
    AIModelDecisionLog,
    AIModelPolicy,
    AIProvider,
    AITaskProfile,
    PromptTemplate,
)
from apps.ai.services import (
    AIProviderNotConfigured,
    normalize_allowed_strategies,
    run_ai_prompt,
    run_ai_task,
    select_ai_execution_plan,
    validate_structured_output,
)
from apps.audit.models import AuditLog
from apps.integrations.models import (
    CredentialType,
    IntegrationAccountStatus,
    IntegrationCredential,
    IntegrationProvider,
    ProviderAuthType,
    SyncLogStatus,
)
from apps.integrations.services import (
    connect_integration_account,
    create_sync_log,
    decrypt_credential_payload,
    reconnect_integration_account,
)
from apps.organizations.models import Membership, MembershipRole, MembershipStatus
from apps.organizations.services import create_organization_for_owner

pytestmark = pytest.mark.django_db


def make_user(django_user_model, email="user@example.com", password="SaaSCore!23456", **extra):
    return django_user_model.objects.create_user(email=email, password=password, **extra)


def make_api_key_provider(slug="test-provider"):
    return IntegrationProvider.objects.create(
        name="Test Provider",
        slug=slug,
        category="test",
        auth_type=ProviderAuthType.API_KEY,
        scopes=["read"],
    )


def test_provider_registry_lists_active_providers(django_user_model):
    make_user(django_user_model)
    provider = make_api_key_provider()
    client = APIClient()
    client.force_authenticate(django_user_model.objects.get(email="user@example.com"))

    response = client.get("/api/v1/integrations/providers/")

    assert response.status_code == 200
    providers = response.json()
    assert provider.slug in {item["slug"] for item in providers}
    openai = next(item for item in providers if item["slug"] == "openai")
    assert openai["credential_fields"] == [
        {
            "key": "api_key",
            "label": "OpenAI API key",
            "secret": True,
            "required": True,
        }
    ]
    assert openai["is_customer_configurable"] is True
    assert "config" not in openai


def test_admin_can_connect_api_key_provider_and_secret_is_encrypted(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    provider = make_api_key_provider()
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/v1/integrations/{provider.slug}/connect/",
        {
            "organization_id": organization.id,
            "external_account_id": "external-123",
            "display_name": "External Account",
            "credential_type": CredentialType.API_KEY,
            "credential_payload": {"api_key": "secret-api-key"},
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["has_credential"] is True
    account = organization.integration_accounts.get(provider=provider)
    assert account.status == IntegrationAccountStatus.CONNECTED
    assert "secret-api-key" not in account.credential.encrypted_payload
    assert decrypt_credential_payload(account.credential.encrypted_payload) == {
        "api_key": "secret-api-key"
    }


def test_member_cannot_connect_integration_provider(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    provider = make_api_key_provider()
    client = APIClient()
    client.force_authenticate(member)

    response = client.post(
        f"/api/v1/integrations/{provider.slug}/connect/",
        {
            "organization_id": organization.id,
            "credential_payload": {"api_key": "secret-api-key"},
        },
        format="json",
    )

    assert response.status_code == 403


def test_connect_rejects_platform_managed_provider_and_unsupported_credential_fields(
    django_user_model,
):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    platform_provider = IntegrationProvider.objects.create(
        name="Platform Service",
        slug="platform-service",
        category="platform",
        auth_type=ProviderAuthType.API_KEY,
        config={"customer_configurable": False},
    )
    openai_provider = IntegrationProvider.objects.get(slug="openai")
    client = APIClient()
    client.force_authenticate(owner)

    platform_response = client.post(
        f"/api/v1/integrations/{platform_provider.slug}/connect/",
        {
            "organization_id": organization.id,
            "credential_payload": {"api_key": "platform-secret"},
        },
        format="json",
    )
    unexpected_field_response = client.post(
        f"/api/v1/integrations/{openai_provider.slug}/connect/",
        {
            "organization_id": organization.id,
            "credential_payload": {
                "api_key": "organization-secret",
                "admin_secret": "not-allowed",
            },
        },
        format="json",
    )

    assert platform_response.status_code == 400
    assert "managed by the SaaS platform" in str(platform_response.json())
    assert unexpected_field_response.status_code == 400
    assert "Unsupported credential fields" in str(unexpected_field_response.json())
    assert organization.integration_accounts.count() == 0


@override_settings(MAX_JSON_PAYLOAD_BYTES=20)
def test_connect_integration_rejects_oversized_json_payloads(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    provider = make_api_key_provider()
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/v1/integrations/{provider.slug}/connect/",
        {
            "organization_id": organization.id,
            "credential_payload": {"api_key": "x" * 100},
            "metadata": {"label": "x" * 100},
        },
        format="json",
    )

    assert response.status_code == 400
    assert "credential_payload" in response.json()


def test_connect_integration_rejects_non_object_json_payloads(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    provider = make_api_key_provider()
    client = APIClient()
    client.force_authenticate(owner)

    credential_response = client.post(
        f"/api/v1/integrations/{provider.slug}/connect/",
        {
            "organization_id": organization.id,
            "credential_payload": "secret-api-key",
            "metadata": {"label": "primary"},
        },
        format="json",
    )
    metadata_response = client.post(
        f"/api/v1/integrations/{provider.slug}/connect/",
        {
            "organization_id": organization.id,
            "credential_payload": {"api_key": "secret-api-key"},
            "metadata": [],
        },
        format="json",
    )

    assert credential_response.status_code == 400
    assert metadata_response.status_code == 400
    assert "credential_payload" in credential_response.json()
    assert "metadata" in metadata_response.json()
    assert organization.integration_accounts.count() == 0


def test_oauth_provider_returns_descriptive_error_until_oauth_client_exists(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    provider = IntegrationProvider.objects.create(
        name="OAuth Provider",
        slug="oauth-provider",
        category="test",
        auth_type=ProviderAuthType.OAUTH2,
        scopes=["read"],
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/v1/integrations/{provider.slug}/connect/",
        {"organization_id": organization.id},
        format="json",
    )

    assert response.status_code == 503
    assert "provider is not configured yet" in response.json()["detail"]


def test_disconnect_and_sync_logs_are_org_scoped(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    provider = make_api_key_provider()
    account = organization.integration_accounts.create(
        provider=provider,
        external_account_id="external-123",
        display_name="External Account",
        connected_by=owner,
    )
    IntegrationCredential.objects.create(
        integration_account=account,
        credential_type=CredentialType.API_KEY,
        encrypted_payload="encrypted-test-payload",
    )
    create_sync_log(
        integration_account=account,
        action="manual_sync",
        status=SyncLogStatus.SUCCEEDED,
        external_request_id="req_123",
    )
    client = APIClient()
    client.force_authenticate(owner)

    logs_response = client.get(f"/api/v1/integrations/{account.id}/sync-logs/")
    disconnect_response = client.post(f"/api/v1/integrations/{account.id}/disconnect/")

    assert logs_response.status_code == 200
    assert logs_response.json()["results"][0]["external_request_id"] == "req_123"
    assert disconnect_response.status_code == 200
    account.refresh_from_db()
    assert account.status == IntegrationAccountStatus.DISCONNECTED
    assert account.external_account_id == ""
    assert account.scopes == []
    assert account.metadata["credential_deleted"] is True
    assert not IntegrationCredential.objects.filter(integration_account=account).exists()


def test_admin_can_reconnect_disconnected_api_key_account(django_user_model):
    owner = make_user(django_user_model, email="reconnect-owner@example.com")
    organization = create_organization_for_owner(owner, "Reconnect Workspace")
    provider = make_api_key_provider()
    account = organization.integration_accounts.create(
        provider=provider,
        display_name="Disconnected Account",
        connected_by=owner,
        status=IntegrationAccountStatus.DISCONNECTED,
        metadata={"credential_deleted": True},
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/v1/integrations/{account.id}/reconnect/",
        {
            "external_account_id": "external-reconnected",
            "credential_type": CredentialType.API_KEY,
            "credential_payload": {"api_key": "new-secret-api-key"},
        },
        format="json",
    )

    assert response.status_code == 200
    account.refresh_from_db()
    assert account.status == IntegrationAccountStatus.CONNECTED
    assert account.external_account_id == "external-reconnected"
    assert account.metadata.get("credential_deleted") is None
    assert decrypt_credential_payload(account.credential.encrypted_payload) == {
        "api_key": "new-secret-api-key"
    }
    assert account.sync_logs.filter(action="reconnect", status=SyncLogStatus.SUCCEEDED).exists()
    assert AuditLog.objects.filter(
        action="integrations.account.reconnected",
        organization=organization,
    ).exists()


def test_reconnect_preserves_existing_account_identity_when_omitted(django_user_model):
    owner = make_user(django_user_model, email="expired-reconnect@example.com")
    organization = create_organization_for_owner(owner, "Expired Reconnect Workspace")
    provider = make_api_key_provider()
    account = organization.integration_accounts.create(
        provider=provider,
        external_account_id="external-existing",
        display_name="Expired Account",
        connected_by=owner,
        status=IntegrationAccountStatus.EXPIRED,
        scopes=["read:existing"],
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/v1/integrations/{account.id}/reconnect/",
        {
            "credential_type": CredentialType.API_KEY,
            "credential_payload": {"api_key": "replacement-key"},
        },
        format="json",
    )

    assert response.status_code == 200
    account.refresh_from_db()
    assert account.external_account_id == "external-existing"
    assert account.scopes == ["read:existing"]


def test_member_cannot_read_integration_sync_logs(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    provider = make_api_key_provider()
    account = organization.integration_accounts.create(
        provider=provider,
        external_account_id="external-123",
        display_name="External Account",
        connected_by=owner,
    )
    create_sync_log(
        integration_account=account,
        action="manual_sync",
        status=SyncLogStatus.FAILED,
        error_message="Sensitive provider error",
        external_request_id="req_private",
    )
    client = APIClient()
    client.force_authenticate(member)

    response = client.get(f"/api/v1/integrations/{account.id}/sync-logs/")

    assert response.status_code == 403


def test_member_integration_account_list_exposes_only_safe_connection_status(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    provider = make_api_key_provider("safe-summary-provider")
    account = organization.integration_accounts.create(
        provider=provider,
        external_account_id="external-private",
        display_name="Safe Summary Provider",
        connected_by=owner,
        scopes=["private:scope"],
        metadata={"private_label": "do-not-expose"},
    )
    IntegrationCredential.objects.create(
        integration_account=account,
        credential_type=CredentialType.API_KEY,
        encrypted_payload="encrypted-test-payload",
    )
    client = APIClient()
    client.force_authenticate(member)

    response = client.get(f"/api/v1/integrations/accounts/?organization_id={organization.id}")

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert set(result) == {
        "id",
        "organization",
        "provider",
        "display_name",
        "status",
        "has_credential",
        "last_sync_at",
        "created_at",
        "updated_at",
    }
    assert "external-private" not in str(result)
    assert "do-not-expose" not in str(result)


def test_invalid_encrypted_integration_credential_is_rejected():
    with pytest.raises(ValidationError, match="could not be decrypted"):
        decrypt_credential_payload("not-a-valid-fernet-token")


def test_disabled_provider_cannot_connect_or_reconnect(django_user_model):
    owner = make_user(django_user_model, email="disabled-provider@example.com")
    organization = create_organization_for_owner(owner, "Disabled Provider Workspace")
    provider = make_api_key_provider("disabled-provider")
    provider.is_active = False
    provider.save(update_fields=["is_active", "updated_at"])
    account = organization.integration_accounts.create(
        provider=provider,
        display_name="Disabled Account",
        connected_by=owner,
        status=IntegrationAccountStatus.DISCONNECTED,
    )

    with pytest.raises(ValidationError, match="provider is disabled"):
        connect_integration_account(
            organization=organization,
            provider=provider,
            connected_by=owner,
            credential_payload={"api_key": "secret"},
        )
    with pytest.raises(ValidationError, match="provider is disabled"):
        reconnect_integration_account(
            account,
            connected_by=owner,
            credential_payload={"api_key": "secret"},
        )


def test_api_key_provider_requires_credential_for_connect_and_reconnect(django_user_model):
    owner = make_user(django_user_model, email="missing-key@example.com")
    organization = create_organization_for_owner(owner, "Missing Key Workspace")
    provider = make_api_key_provider("missing-key-provider")
    account = organization.integration_accounts.create(
        provider=provider,
        display_name="Missing Key Account",
        connected_by=owner,
        status=IntegrationAccountStatus.DISCONNECTED,
    )

    with pytest.raises(ValidationError, match="require a credential payload"):
        connect_integration_account(
            organization=organization,
            provider=provider,
            connected_by=owner,
        )
    with pytest.raises(ValidationError, match="require a credential payload"):
        reconnect_integration_account(account, connected_by=owner)


def test_default_ai_providers_expose_only_public_metadata(django_user_model):
    user = make_user(django_user_model, email="owner@example.com")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/ai/providers/")

    assert response.status_code == 200
    slugs = {provider["slug"] for provider in response.json()}
    assert {"openai", "anthropic", "gemini"}.issubset(slugs)
    openai_provider = next(provider for provider in response.json() if provider["slug"] == "openai")
    assert set(openai_provider) == {"id", "name", "slug", "status"}
    assert "default_model" not in openai_provider
    assert "supported_features" not in openai_provider
    assert "configuration" not in openai_provider


def test_prompt_templates_and_model_policies_require_staff_user(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    staff = make_user(django_user_model, email="staff@example.com", is_staff=True)
    client = APIClient()
    client.force_authenticate(owner)

    prompt_response = client.get("/api/v1/ai/prompt-templates/")
    policy_response = client.get("/api/v1/ai/model-policies/")

    assert prompt_response.status_code == 403
    assert policy_response.status_code == 403

    client.force_authenticate(staff)
    assert client.get("/api/v1/ai/prompt-templates/").status_code == 200
    assert client.get("/api/v1/ai/model-policies/").status_code == 200


def test_structured_output_validation_passes_and_fails():
    schema = {
        "type": "object",
        "required": ["summary"],
        "properties": {"summary": {"type": "string"}},
    }

    assert validate_structured_output({"summary": "ok"}, schema) is True

    with pytest.raises(ValidationError):
        validate_structured_output({"summary": 123}, schema)


def test_ai_prompt_service_logs_failed_call_when_provider_key_is_missing(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    provider = AIProvider.objects.get(slug="openai")
    PromptTemplate.objects.create(
        key="generic-summary",
        name="Generic Summary",
        version=1,
        system_prompt="Return structured JSON.",
        user_prompt="Summarize {{input}}",
        output_schema={
            "type": "object",
            "required": ["summary"],
            "properties": {"summary": {"type": "string"}},
        },
    )

    with pytest.raises(AIProviderNotConfigured):
        run_ai_prompt(
            organization=organization,
            user=owner,
            provider_slug=provider.slug,
            prompt_key="generic-summary",
            input_payload={"input": "hello"},
        )

    log = AICallLog.objects.get(organization=organization)
    assert log.status == AICallStatus.FAILED
    assert log.provider == provider
    assert log.prompt_version == 1
    assert "OPENAI_API_KEY" in log.error_message


def test_ai_call_logs_are_organization_scoped(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    other = make_user(django_user_model, email="other@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    other_organization = create_organization_for_owner(other, "Other Workspace")
    provider = AIProvider.objects.get(slug="openai")
    prompt = PromptTemplate.objects.create(
        key="generic-summary",
        name="Generic Summary",
        version=1,
        user_prompt="Summarize {{input}}",
    )
    AICallLog.objects.create(
        organization=organization,
        user=owner,
        provider=provider,
        prompt_template=prompt,
        prompt_version=1,
        model="test-model",
        status=AICallStatus.FAILED,
        request_hash="a" * 64,
    )
    AICallLog.objects.create(
        organization=other_organization,
        user=other,
        provider=provider,
        prompt_template=prompt,
        prompt_version=1,
        model="test-model",
        status=AICallStatus.FAILED,
        request_hash="b" * 64,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(f"/api/v1/ai/call-logs/?organization_id={organization.id}")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["request_hash"] == "a" * 64


def test_ai_call_logs_require_admin_role(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    provider = AIProvider.objects.get(slug="openai")
    prompt = PromptTemplate.objects.create(
        key="generic-summary",
        name="Generic Summary",
        version=1,
        user_prompt="Summarize {{input}}",
    )
    AICallLog.objects.create(
        organization=organization,
        user=owner,
        provider=provider,
        prompt_template=prompt,
        prompt_version=1,
        model="test-model",
        status=AICallStatus.FAILED,
        request_hash="a" * 64,
    )
    client = APIClient()
    client.force_authenticate(member)

    response = client.get(f"/api/v1/ai/call-logs/?organization_id={organization.id}")

    assert response.status_code == 403


def test_default_ai_task_profiles_are_exposed(django_user_model):
    user = make_user(django_user_model, email="owner@example.com")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/ai/task-profiles/")

    assert response.status_code == 200
    profiles = response.json()["results"]
    profile_keys = {profile["key"] for profile in profiles}
    assert {"recurring_ai_report", "table_analysis", "high_risk_advice"}.issubset(
        profile_keys
    )
    table_profile = next(profile for profile in profiles if profile["key"] == "table_analysis")
    assert set(table_profile) == {"id", "key", "name", "description", "product_area"}
    assert "default_strategy" not in table_profile
    assert "allowed_strategies" not in table_profile
    assert "expected_runs_per_month" not in table_profile
    assert "max_cost_per_run" not in table_profile
    assert "quality_threshold" not in table_profile
    assert "config" not in table_profile


def test_execution_plan_prefers_deterministic_strategy_when_problem_allows_it(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/ai/execution-plan/",
        {
            "organization_id": organization.id,
            "task_key": "table_analysis",
            "input_payload": {"columns": ["revenue", "month"], "rows": 12},
            "constraints": {"can_solve_without_ai": True},
        },
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "deterministic"
    assert body["provider_slug"] == ""
    assert body["configuration"]["status"] == "not_required"
    assert AIModelDecisionLog.objects.filter(
        organization=organization,
        selected_strategy="deterministic",
    ).exists()


def test_execution_plan_uses_classic_ml_for_table_analysis_when_available(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")

    execution_plan = select_ai_execution_plan(
        organization=organization,
        user=owner,
        task_key="table_analysis",
        input_payload={"metric": "churn", "rows": 5000},
        constraints={"can_use_classic_ml": True},
    )

    assert execution_plan["strategy"] == "classic_ml"
    assert execution_plan["provider_slug"] == ""
    assert execution_plan["fallback"]["strategy"] == "low_cost_llm"
    assert execution_plan["reason"] == "Task can be solved by classic ML/DL libraries."


def test_public_execution_plan_ignores_privileged_client_constraints(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/ai/execution-plan/",
        {
            "organization_id": organization.id,
            "task_key": "table_analysis",
            "input_payload": {"metric": "revenue", "rows": 5000},
            "constraints": {
                "can_use_classic_ml": True,
                "force_strategy": "advanced_llm",
                "requires_advanced_reasoning": True,
                "expected_runs_per_month": 1,
            },
        },
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "classic_ml"
    assert body["provider_slug"] == ""
    assert "force_strategy" not in body["constraints"]
    assert "requires_advanced_reasoning" not in body["constraints"]
    assert "expected_runs_per_month" not in body["constraints"]


def test_execution_plan_rejects_non_object_constraints(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/ai/execution-plan/",
        {
            "organization_id": organization.id,
            "task_key": "table_analysis",
            "input_payload": {"metric": "revenue", "rows": 5000},
            "constraints": ["can_use_classic_ml"],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "constraints" in response.json()
    assert not AIModelDecisionLog.objects.filter(organization=organization).exists()


def test_execution_plan_uses_low_cost_llm_for_recurring_report_narrative(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")

    execution_plan = select_ai_execution_plan(
        organization=organization,
        user=owner,
        task_key="recurring_ai_report",
        input_payload={"facts": {"revenue": 1000, "trend": "up"}},
        constraints={},
    )

    assert execution_plan["strategy"] == "low_cost_llm"
    assert execution_plan["provider_slug"] == "openai"
    assert execution_plan["configuration"]["status"] == "not_configured"
    assert "OPENAI_API_KEY" in execution_plan["configuration"]["detail"]


def test_execution_plan_recognizes_encrypted_organization_ai_api_key(django_user_model):
    owner = make_user(django_user_model, email="byok-owner@example.com")
    organization = create_organization_for_owner(owner, "BYOK Workspace")
    provider = IntegrationProvider.objects.get(slug="openai")
    connect_integration_account(
        organization=organization,
        provider=provider,
        connected_by=owner,
        credential_payload={"api_key": "organization-openai-secret"},
    )

    execution_plan = select_ai_execution_plan(
        organization=organization,
        user=owner,
        task_key="recurring_ai_report",
        input_payload={"facts": {"revenue": 1000}},
        constraints={},
    )

    assert execution_plan["configuration"] == {
        "status": "configured",
        "detail": "Organization API key is configured.",
    }
    assert "organization-openai-secret" not in str(execution_plan)


def test_llm_execution_plan_reports_missing_required_provider(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    AIProvider.objects.update(is_active=False)

    execution_plan = select_ai_execution_plan(
        organization=organization,
        user=owner,
        task_key="recurring_ai_report",
        input_payload={"facts": {"revenue": 1000}},
        constraints={},
    )

    assert execution_plan["strategy"] == "low_cost_llm"
    assert execution_plan["provider_slug"] == ""
    assert execution_plan["configuration"]["status"] == "not_configured"
    assert "requires an active provider" in execution_plan["configuration"]["detail"]


def test_high_risk_execution_plan_requires_human_review(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")

    execution_plan = select_ai_execution_plan(
        organization=organization,
        user=owner,
        task_key="high_risk_advice",
        input_payload={"case": "sensitive"},
        constraints={"risk_level": "high"},
        trusted_constraints=True,
    )

    assert execution_plan["strategy"] == "human_review"
    assert execution_plan["requires_human_review"] is True
    assert execution_plan["provider_slug"] == ""


def test_trusted_ai_constraints_can_force_allowed_strategy_and_reject_disallowed_strategy(
    django_user_model,
):
    owner = make_user(django_user_model, email="forced-strategy@example.com")
    organization = create_organization_for_owner(owner, "Forced Strategy Workspace")

    execution_plan = select_ai_execution_plan(
        organization=organization,
        user=owner,
        task_key="table_analysis",
        constraints={"force_strategy": AIExecutionStrategy.LOCAL_MODEL},
        trusted_constraints=True,
    )

    assert execution_plan["strategy"] == AIExecutionStrategy.LOCAL_MODEL
    assert execution_plan["reason"] == "Forced by request constraints."

    with pytest.raises(ValidationError, match="Forced strategy is not allowed"):
        select_ai_execution_plan(
            organization=organization,
            user=owner,
            task_key="table_analysis",
            constraints={
                "force_strategy": AIExecutionStrategy.HUMAN_REVIEW,
                "allowed_strategies": [AIExecutionStrategy.DETERMINISTIC],
            },
            trusted_constraints=True,
        )


def test_ai_execution_plan_uses_local_model_and_cost_sensitive_fallbacks(django_user_model):
    owner = make_user(django_user_model, email="local-model@example.com")
    organization = create_organization_for_owner(owner, "Local Model Workspace")

    local_plan = select_ai_execution_plan(
        organization=organization,
        user=owner,
        task_key="table_analysis",
        constraints={"can_use_local_model": True},
    )
    cost_sensitive_plan = select_ai_execution_plan(
        organization=organization,
        user=owner,
        task_key="recurring_ai_report",
        constraints={"cost_sensitivity": "high"},
    )

    assert local_plan["strategy"] == AIExecutionStrategy.LOCAL_MODEL
    assert local_plan["configuration"]["status"] == "not_required"
    assert cost_sensitive_plan["strategy"] == AIExecutionStrategy.LOW_COST_LLM
    assert cost_sensitive_plan["reason"] == "High-volume/cost-sensitive task."


def test_ai_plan_specific_policy_overrides_generic_policy(django_user_model):
    owner = make_user(django_user_model, email="policy@example.com")
    organization = create_organization_for_owner(owner, "Policy Workspace")
    organization.subscription.plan = organization.subscription.plan.__class__.objects.get(
        slug="pro"
    )
    organization.subscription.status = "active"
    organization.subscription.save(update_fields=["plan", "status", "updated_at"])
    profile = AITaskProfile.objects.get(key="recurring_ai_report")
    provider = AIProvider.objects.get(slug="openai")
    generic = AIModelPolicy.objects.create(
        task_profile=profile,
        name="Generic recurring policy",
        strategy=AIExecutionStrategy.LOW_COST_LLM,
        provider=provider,
        model_name="generic-model",
        priority=1,
    )
    plan_specific = AIModelPolicy.objects.create(
        task_profile=profile,
        name="Pro recurring policy",
        strategy=AIExecutionStrategy.LOW_COST_LLM,
        provider=provider,
        model_name="pro-model",
        plan_slug="pro",
        priority=100,
    )

    execution_plan = select_ai_execution_plan(
        organization=organization,
        user=owner,
        task_key=profile.key,
    )

    assert execution_plan["policy_id"] == plan_specific.id
    assert execution_plan["policy_id"] != generic.id
    assert execution_plan["model"] == "pro-model"


def test_ai_allowed_strategy_validation_rejects_invalid_and_empty_configuration():
    profile = AITaskProfile.objects.get(key="table_analysis")
    profile.allowed_strategies = ["unsupported"]

    with pytest.raises(ValidationError, match="Unsupported AI execution strategy"):
        normalize_allowed_strategies(profile)

    profile.allowed_strategies = [AIExecutionStrategy.DETERMINISTIC]
    with pytest.raises(ValidationError, match="No valid AI strategies"):
        normalize_allowed_strategies(
            profile,
            {"allowed_strategies": [AIExecutionStrategy.LOW_COST_LLM]},
        )


def test_run_ai_task_returns_product_executor_instruction_for_non_llm_strategy(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    PromptTemplate.objects.create(
        key="table-summary",
        name="Table Summary",
        version=1,
        user_prompt="Summarize {{input}}",
    )

    result = run_ai_task(
        organization=organization,
        user=owner,
        task_key="table_analysis",
        prompt_key="table-summary",
        input_payload={"rows": 12},
        constraints={"can_solve_without_ai": True},
    )

    assert result["status"] == "selected"
    assert result["execution_plan"]["strategy"] == "deterministic"
    assert "product-specific" in result["detail"]


def test_run_ai_task_rejects_llm_execution_without_active_provider(django_user_model):
    owner = make_user(django_user_model, email="no-provider@example.com")
    organization = create_organization_for_owner(owner, "No Provider Workspace")
    AIProvider.objects.update(is_active=False)

    with pytest.raises(AIProviderNotConfigured, match="No active LLM provider"):
        run_ai_task(
            organization=organization,
            user=owner,
            task_key="recurring_ai_report",
            prompt_key="missing-prompt",
            input_payload={"facts": {"revenue": 1000}},
        )


def test_run_ai_prompt_rejects_missing_prompt_without_creating_call_log(django_user_model):
    owner = make_user(django_user_model, email="missing-prompt@example.com")
    organization = create_organization_for_owner(owner, "Missing Prompt Workspace")

    with pytest.raises(ValidationError, match="No active prompt template"):
        run_ai_prompt(
            organization=organization,
            user=owner,
            provider_slug="openai",
            prompt_key="missing-prompt",
            input_payload={"facts": {"revenue": 1000}},
        )

    assert not AICallLog.objects.filter(organization=organization).exists()


def test_ai_decision_logs_are_organization_scoped(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    other = make_user(django_user_model, email="other@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    other_organization = create_organization_for_owner(other, "Other Workspace")
    profile = AITaskProfile.objects.get(key="table_analysis")
    AIModelDecisionLog.objects.create(
        organization=organization,
        user=owner,
        task_profile=profile,
        task_key=profile.key,
        selected_strategy="classic_ml",
        decision_reason="test",
    )
    AIModelDecisionLog.objects.create(
        organization=other_organization,
        user=other,
        task_profile=profile,
        task_key=profile.key,
        selected_strategy="classic_ml",
        decision_reason="test",
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(f"/api/v1/ai/decision-logs/?organization_id={organization.id}")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["organization"] == organization.id


def test_ai_decision_logs_require_admin_role(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    profile = AITaskProfile.objects.get(key="table_analysis")
    AIModelDecisionLog.objects.create(
        organization=organization,
        user=owner,
        task_profile=profile,
        task_key=profile.key,
        selected_strategy="classic_ml",
        decision_reason="test",
    )
    client = APIClient()
    client.force_authenticate(member)

    response = client.get(f"/api/v1/ai/decision-logs/?organization_id={organization.id}")

    assert response.status_code == 403

from django.db import migrations


CUSTOMER_MANAGED_PROVIDERS = [
    {
        "slug": "openai",
        "name": "OpenAI",
        "category": "ai",
        "auth_type": "api_key",
        "feature_flags": {"byok": True},
        "config": {
            "customer_configurable": True,
            "description": "Use an organization-owned OpenAI API key.",
            "credential_fields": [
                {"key": "api_key", "label": "OpenAI API key", "secret": True, "required": True}
            ],
        },
    },
    {
        "slug": "anthropic",
        "name": "Anthropic",
        "category": "ai",
        "auth_type": "api_key",
        "feature_flags": {"byok": True},
        "config": {
            "customer_configurable": True,
            "description": "Use an organization-owned Anthropic API key.",
            "credential_fields": [
                {"key": "api_key", "label": "Anthropic API key", "secret": True, "required": True}
            ],
        },
    },
    {
        "slug": "gemini",
        "name": "Google Gemini",
        "category": "ai",
        "auth_type": "api_key",
        "feature_flags": {"byok": True},
        "config": {
            "customer_configurable": True,
            "description": "Use an organization-owned Gemini API key.",
            "credential_fields": [
                {"key": "api_key", "label": "Gemini API key", "secret": True, "required": True}
            ],
        },
    },
    {
        "slug": "slack",
        "name": "Slack",
        "category": "notifications",
        "auth_type": "oauth2",
        "scopes": [],
        "feature_flags": {"byok": False},
        "config": {
            "customer_configurable": True,
            "description": "Connect a Slack workspace through OAuth.",
            "oauth_client_configured": False,
            "credential_fields": [],
        },
    },
]


def seed_customer_managed_providers(apps, schema_editor):
    IntegrationProvider = apps.get_model("integrations", "IntegrationProvider")
    for provider_data in CUSTOMER_MANAGED_PROVIDERS:
        defaults = provider_data.copy()
        slug = defaults.pop("slug")
        IntegrationProvider.objects.update_or_create(slug=slug, defaults=defaults)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_customer_managed_providers, noop_reverse),
    ]

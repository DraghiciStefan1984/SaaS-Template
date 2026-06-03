from django.db import migrations


DEFAULT_AI_PROVIDERS = [
    {
        "slug": "openai",
        "name": "OpenAI",
        "default_model": "",
        "supported_features": {
            "structured_outputs": True,
            "prompt_caching": True,
            "tool_use": True,
        },
        "config": {
            "api_key_setting": "OPENAI_API_KEY",
        },
    },
    {
        "slug": "anthropic",
        "name": "Anthropic",
        "default_model": "",
        "supported_features": {
            "structured_outputs": True,
            "prompt_caching": True,
            "tool_use": True,
        },
        "config": {
            "api_key_setting": "ANTHROPIC_API_KEY",
        },
    },
    {
        "slug": "gemini",
        "name": "Gemini",
        "default_model": "",
        "supported_features": {
            "structured_outputs": True,
            "prompt_caching": True,
            "tool_use": True,
        },
        "config": {
            "api_key_setting": "GEMINI_API_KEY",
        },
    },
]


def seed_default_ai_providers(apps, schema_editor):
    AIProvider = apps.get_model("ai", "AIProvider")
    for provider_data in DEFAULT_AI_PROVIDERS:
        defaults = provider_data.copy()
        slug = defaults.pop("slug")
        AIProvider.objects.update_or_create(slug=slug, defaults=defaults)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_default_ai_providers, noop_reverse),
    ]


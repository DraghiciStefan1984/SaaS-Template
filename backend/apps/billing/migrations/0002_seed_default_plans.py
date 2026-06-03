from django.db import migrations


DEFAULT_PLANS = [
    {
        "slug": "free",
        "name": "Free",
        "description": "Validation plan for early trials and demos.",
        "display_order": 0,
        "features": {
            "team_members": False,
            "scheduled_reports": False,
            "white_label_reports": False,
        },
        "limits": {
            "one_click_requests": 3,
            "generated_reports": 1,
            "active_monitors": 1,
            "integration_accounts": 1,
            "ai_tokens": 10000,
        },
    },
    {
        "slug": "starter",
        "name": "Starter",
        "description": "Solo and small business plan.",
        "display_order": 10,
        "features": {
            "team_members": False,
            "scheduled_reports": True,
            "white_label_reports": False,
        },
        "limits": {
            "one_click_requests": 100,
            "generated_reports": 30,
            "active_monitors": 3,
            "integration_accounts": 3,
            "ai_tokens": 250000,
        },
    },
    {
        "slug": "pro",
        "name": "Pro",
        "description": "Growing business plan.",
        "display_order": 20,
        "features": {
            "team_members": True,
            "scheduled_reports": True,
            "white_label_reports": False,
        },
        "limits": {
            "one_click_requests": 1000,
            "generated_reports": 300,
            "active_monitors": 10,
            "integration_accounts": 10,
            "ai_tokens": 1000000,
        },
    },
    {
        "slug": "agency",
        "name": "Agency",
        "description": "Multi-client and multi-location plan.",
        "display_order": 30,
        "features": {
            "team_members": True,
            "scheduled_reports": True,
            "white_label_reports": True,
        },
        "limits": {
            "one_click_requests": 10000,
            "generated_reports": 3000,
            "active_monitors": 100,
            "integration_accounts": 100,
            "ai_tokens": 10000000,
        },
    },
]


def seed_default_plans(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for plan_data in DEFAULT_PLANS:
        defaults = plan_data.copy()
        slug = defaults.pop("slug")
        Plan.objects.update_or_create(slug=slug, defaults=defaults)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_default_plans, noop_reverse),
    ]

from django.db import migrations


REPORT_TEMPLATES = [
    {
        "key": "weekly_summary",
        "name": "Weekly summary",
        "description": "Reusable weekly report scaffold for product metrics and narrative summary.",
        "default_format": "json",
        "ai_task_profile_key": "recurring_ai_report",
        "config": {
            "sections": ["overview", "key_metrics", "risks", "recommended_actions"],
        },
    },
    {
        "key": "table_analysis",
        "name": "Table analysis",
        "description": "Reusable report scaffold for deterministic/statistical table analysis.",
        "default_format": "json",
        "ai_task_profile_key": "table_analysis",
        "config": {
            "sections": ["data_quality", "patterns", "outliers", "conclusion"],
        },
    },
]


def seed_default_report_templates(apps, schema_editor):
    ReportTemplate = apps.get_model("reports", "ReportTemplate")
    AITaskProfile = apps.get_model("ai", "AITaskProfile")

    for template_data in REPORT_TEMPLATES:
        defaults = template_data.copy()
        key = defaults.pop("key")
        ai_task_profile_key = defaults.pop("ai_task_profile_key")
        defaults["ai_task_profile"] = AITaskProfile.objects.filter(
            key=ai_task_profile_key,
            is_active=True,
        ).first()
        ReportTemplate.objects.update_or_create(key=key, defaults=defaults)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_default_report_templates, noop_reverse),
    ]

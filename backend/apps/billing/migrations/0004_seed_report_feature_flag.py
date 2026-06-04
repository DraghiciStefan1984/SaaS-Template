from django.db import migrations


REPORT_FEATURE_UPDATES = {
    "free": {"features": {"reports": True}, "limits": {"generated_reports": 1}},
    "starter": {"features": {"reports": True}, "limits": {"generated_reports": 30}},
    "pro": {"features": {"reports": True}, "limits": {"generated_reports": 300}},
    "agency": {"features": {"reports": True}, "limits": {"generated_reports": 3000}},
}


def seed_report_feature_flag(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for slug, updates in REPORT_FEATURE_UPDATES.items():
        plan = Plan.objects.filter(slug=slug).first()
        if plan is None:
            continue
        plan.features = {**plan.features, **updates["features"]}
        plan.limits = {**plan.limits, **updates["limits"]}
        plan.save(update_fields=["features", "limits", "updated_at"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0003_seed_product_feature_flags"),
    ]

    operations = [
        migrations.RunPython(seed_report_feature_flag, noop_reverse),
    ]

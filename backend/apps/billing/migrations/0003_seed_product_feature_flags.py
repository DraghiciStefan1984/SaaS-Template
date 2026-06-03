from django.db import migrations


PLAN_FEATURE_UPDATES = {
    "free": {
        "example_insights": True,
        "advanced_ai_models": False,
        "product_feature_flags": True,
    },
    "starter": {
        "example_insights": True,
        "advanced_ai_models": False,
        "product_feature_flags": True,
    },
    "pro": {
        "example_insights": True,
        "advanced_ai_models": True,
        "product_feature_flags": True,
    },
    "agency": {
        "example_insights": True,
        "advanced_ai_models": True,
        "product_feature_flags": True,
    },
}


def seed_product_feature_flags(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for slug, feature_updates in PLAN_FEATURE_UPDATES.items():
        plan = Plan.objects.filter(slug=slug).first()
        if plan is None:
            continue
        plan.features = {**plan.features, **feature_updates}
        plan.save(update_fields=["features", "updated_at"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0002_seed_default_plans"),
    ]

    operations = [
        migrations.RunPython(seed_product_feature_flags, noop_reverse),
    ]

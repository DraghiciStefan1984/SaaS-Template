from decimal import Decimal

from django.db import migrations


DEFAULT_ALLOWED_STRATEGIES = [
    "deterministic",
    "classic_ml",
    "local_model",
    "low_cost_llm",
    "standard_llm",
    "advanced_llm",
    "human_review",
]

TASK_PROFILES = [
    {
        "key": "recurring_ai_report",
        "name": "Recurring AI report",
        "description": "Low-volume weekly or monthly reports with AI-written conclusions.",
        "product_area": "reports",
        "default_strategy": "low_cost_llm",
        "allowed_strategies": DEFAULT_ALLOWED_STRATEGIES,
        "expected_runs_per_month": 8,
        "max_cost_per_run": Decimal("0.050000"),
        "requires_structured_output": True,
        "config": {
            "guidance": "Use deterministic calculations first; use an LLM for the narrative only.",
        },
    },
    {
        "key": "table_analysis",
        "name": "Table analysis",
        "description": "Structured data analysis where rules, statistics, or ML are usually enough.",
        "product_area": "analytics",
        "default_strategy": "classic_ml",
        "allowed_strategies": DEFAULT_ALLOWED_STRATEGIES,
        "expected_runs_per_month": 1000,
        "max_cost_per_run": Decimal("0.005000"),
        "requires_structured_output": True,
        "config": {
            "guidance": "Prefer deterministic/statistical analysis; use LLMs only for final wording.",
        },
    },
    {
        "key": "document_extraction",
        "name": "Document extraction",
        "description": "Extract and normalize information from semi-structured documents.",
        "product_area": "documents",
        "default_strategy": "low_cost_llm",
        "allowed_strategies": DEFAULT_ALLOWED_STRATEGIES,
        "expected_runs_per_month": 300,
        "max_cost_per_run": Decimal("0.030000"),
        "requires_structured_output": True,
    },
    {
        "key": "support_assistant",
        "name": "Support assistant",
        "description": "Customer support drafts, triage, and knowledge-base responses.",
        "product_area": "support",
        "default_strategy": "low_cost_llm",
        "allowed_strategies": [
            "deterministic",
            "low_cost_llm",
            "standard_llm",
            "advanced_llm",
            "human_review",
        ],
        "expected_runs_per_month": 2000,
        "max_cost_per_run": Decimal("0.010000"),
    },
    {
        "key": "high_risk_advice",
        "name": "High-risk advice",
        "description": "Sensitive workflows that require review before users rely on the output.",
        "product_area": "risk",
        "default_strategy": "human_review",
        "allowed_strategies": [
            "standard_llm",
            "advanced_llm",
            "human_review",
        ],
        "expected_runs_per_month": 50,
        "max_cost_per_run": Decimal("0.250000"),
        "is_high_risk": True,
        "requires_structured_output": True,
    },
]

POLICIES = [
    {
        "task_key": "recurring_ai_report",
        "name": "Narrative on low-cost LLM",
        "strategy": "low_cost_llm",
        "priority": 10,
        "fallback_strategy": "standard_llm",
        "rules": {
            "note": "Use after deterministic calculations have produced report facts.",
        },
    },
    {
        "task_key": "table_analysis",
        "name": "Classic analytics first",
        "strategy": "classic_ml",
        "priority": 10,
        "fallback_strategy": "low_cost_llm",
        "rules": {
            "recommended_libraries": ["pandas", "numpy", "scikit-learn"],
        },
    },
    {
        "task_key": "document_extraction",
        "name": "Structured extraction on low-cost LLM",
        "strategy": "low_cost_llm",
        "priority": 10,
        "fallback_strategy": "standard_llm",
        "rules": {
            "requires_validation": True,
        },
    },
    {
        "task_key": "support_assistant",
        "name": "Cheap support draft",
        "strategy": "low_cost_llm",
        "priority": 10,
        "fallback_strategy": "standard_llm",
        "rules": {
            "fallback_when": "low confidence, policy uncertainty, or escalated customer tier",
        },
    },
    {
        "task_key": "high_risk_advice",
        "name": "Human review default",
        "strategy": "human_review",
        "priority": 10,
        "fallback_strategy": "",
        "rules": {
            "note": "Do not deliver final advice without a product-specific review workflow.",
        },
    },
]


def seed_default_ai_task_profiles(apps, schema_editor):
    AITaskProfile = apps.get_model("ai", "AITaskProfile")
    AIModelPolicy = apps.get_model("ai", "AIModelPolicy")
    AIProvider = apps.get_model("ai", "AIProvider")

    openai_provider = AIProvider.objects.filter(slug="openai").first()
    profiles_by_key = {}
    for profile_data in TASK_PROFILES:
        defaults = profile_data.copy()
        key = defaults.pop("key")
        profile, _created = AITaskProfile.objects.update_or_create(key=key, defaults=defaults)
        profiles_by_key[key] = profile

    for policy_data in POLICIES:
        task_key = policy_data["task_key"]
        defaults = policy_data.copy()
        defaults.pop("task_key")
        if defaults["strategy"] in {"low_cost_llm", "standard_llm", "advanced_llm"}:
            defaults["provider"] = openai_provider
        AIModelPolicy.objects.update_or_create(
            task_profile=profiles_by_key[task_key],
            name=defaults.pop("name"),
            defaults=defaults,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0003_aitaskprofile_aimodelpolicy_aimodeldecisionlog_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_default_ai_task_profiles, noop_reverse),
    ]

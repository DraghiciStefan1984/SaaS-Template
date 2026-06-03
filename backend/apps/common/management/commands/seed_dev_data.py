from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import UserAccountStatus
from apps.integrations.models import IntegrationProvider, ProviderAuthType, ProviderStatus
from apps.notifications.models import NotificationChannel, NotificationEvent
from apps.notifications.services import create_delivery_log, upsert_notification_preference
from apps.organizations.models import Membership, MembershipStatus, Organization
from apps.organizations.services import create_organization_for_owner
from apps.products.example_insights.models import ExampleInsightRequest
from apps.products.example_insights.services import create_example_insight_request


class Command(BaseCommand):
    help = "Seed local development data for the reusable SaaS template."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo@example.com")
        parser.add_argument("--password", default="SaaSCore!23456")
        parser.add_argument("--organization", default="Demo Workspace")
        parser.add_argument(
            "--skip-password-reset",
            action="store_true",
            help="Keep the existing password if the demo user already exists.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        email = options["email"]
        password = options["password"]
        organization_name = options["organization"]
        skip_password_reset = options["skip_password_reset"]

        user, user_created = User.objects.get_or_create(
            email=email,
            defaults={
                "name": "Demo User",
                "is_email_verified": True,
                "account_status": UserAccountStatus.ACTIVE,
            },
        )
        fields_to_update = []
        if not user.name:
            user.name = "Demo User"
            fields_to_update.append("name")
        if not user.is_email_verified:
            user.is_email_verified = True
            fields_to_update.append("is_email_verified")
        if user.account_status != UserAccountStatus.ACTIVE:
            user.account_status = UserAccountStatus.ACTIVE
            fields_to_update.append("account_status")
        if user_created or not skip_password_reset:
            user.set_password(password)
            fields_to_update.append("password")
        if fields_to_update:
            user.save(update_fields=sorted(set(fields_to_update)))

        organization = (
            Organization.objects.filter(owner=user, name=organization_name).first()
            or Membership.objects.filter(
                user=user,
                status=MembershipStatus.ACTIVE,
                organization__name=organization_name,
            )
            .select_related("organization")
            .values_list("organization", flat=True)
            .first()
        )
        if isinstance(organization, int):
            organization = Organization.objects.get(id=organization)
        if organization is None:
            organization = create_organization_for_owner(user, organization_name)

        insight_request = ExampleInsightRequest.objects.filter(
            organization=organization,
            title="Demo Table Insight",
        ).first()
        if insight_request is None:
            insight_request = create_example_insight_request(
                organization=organization,
                created_by=user,
                title="Demo Table Insight",
                input_payload={
                    "rows": [
                        {"month": "January", "revenue": 1000, "users": 75},
                        {"month": "February", "revenue": 1250, "users": 91},
                    ],
                    "metrics": ["revenue", "users"],
                },
                constraints={
                    "can_use_classic_ml": True,
                },
            )

        for provider in self.default_integration_providers():
            IntegrationProvider.objects.update_or_create(
                slug=provider["slug"],
                defaults=provider,
            )

        upsert_notification_preference(
            organization=organization,
            event=NotificationEvent.REPORT_READY,
            channel=NotificationChannel.EMAIL,
            is_enabled=True,
            config={"source": "seed_dev_data"},
        )
        delivery_log = organization.notification_delivery_logs.filter(
            event=NotificationEvent.REPORT_READY,
            channel=NotificationChannel.EMAIL,
            subject="Demo notification: report ready",
        ).first()
        if delivery_log is None:
            delivery_log = create_delivery_log(
                organization=organization,
                user=user,
                event=NotificationEvent.REPORT_READY,
                channel=NotificationChannel.EMAIL,
                recipient=user.email,
                subject="Demo notification: report ready",
                payload={
                    "report_id": insight_request.report_id,
                    "insight_request_id": insight_request.id,
                },
                provider="console",
                metadata={"source": "seed_dev_data"},
            )
            delivery_log.mark_sent(provider_message_id=f"seed-{delivery_log.id}")

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded dev data: "
                f"user={user.email}, organization={organization.name}, "
                f"example_insight_request_id={insight_request.id}, "
                f"password={'unchanged' if skip_password_reset else 'reset'}"
            )
        )

    def default_integration_providers(self):
        return [
            {
                "name": "CSV Upload",
                "slug": "csv-upload",
                "category": "data",
                "auth_type": ProviderAuthType.NONE,
                "scopes": [],
                "status": ProviderStatus.AVAILABLE,
                "feature_flags": {"demo_ready": True},
                "config": {"source": "seed_dev_data"},
                "is_active": True,
            },
            {
                "name": "Google Sheets",
                "slug": "google-sheets",
                "category": "data",
                "auth_type": ProviderAuthType.OAUTH2,
                "scopes": ["spreadsheets.readonly"],
                "status": ProviderStatus.BETA,
                "feature_flags": {"requires_external_account": True},
                "config": {"source": "seed_dev_data"},
                "is_active": True,
            },
            {
                "name": "Slack",
                "slug": "slack",
                "category": "notifications",
                "auth_type": ProviderAuthType.OAUTH2,
                "scopes": ["chat:write"],
                "status": ProviderStatus.BETA,
                "feature_flags": {"requires_external_account": True},
                "config": {"source": "seed_dev_data"},
                "is_active": True,
            },
        ]

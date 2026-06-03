import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

function parseArgs(argv) {
  const options = { dryRun: false, force: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--dry-run") {
      options.dryRun = true;
    } else if (arg === "--force") {
      options.force = true;
    } else if (arg === "--slug") {
      options.slug = argv[++index];
    } else if (arg === "--name") {
      options.name = argv[++index];
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return options;
}

function requireValidSlug(slug) {
  if (!slug || !/^[a-z][a-z0-9-]*$/.test(slug)) {
    throw new Error("Use --slug with kebab-case, for example: customer-health");
  }
}

function toSnakeCase(slug) {
  return slug.replaceAll("-", "_");
}

function toPascalCase(slug) {
  return slug
    .split("-")
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join("");
}

function toTitle(slug, name) {
  if (name) {
    return name;
  }
  return slug
    .split("-")
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

function productFiles({ slug, name }) {
  const snake = toSnakeCase(slug);
  const pascal = toPascalCase(slug);
  const title = toTitle(slug, name);
  const productDir = join("backend", "apps", "products", snake);
  const frontendPage = join("frontend", "src", "pages", `${pascal}Page.tsx`);

  return [
    {
      path: join(productDir, "__init__.py"),
      content: "\n",
    },
    {
      path: join(productDir, "apps.py"),
      content: `from django.apps import AppConfig


class ${pascal}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.products.${snake}"
`,
    },
    {
      path: join(productDir, "models.py"),
      content: `from django.conf import settings
from django.db import models


class ${pascal}RequestStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PLANNED = "planned", "Planned"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class ${pascal}Request(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="${snake}_requests",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="${snake}_requests",
    )
    title = models.CharField(max_length=240)
    status = models.CharField(
        max_length=30,
        choices=${pascal}RequestStatus.choices,
        default=${pascal}RequestStatus.PLANNED,
    )
    input_payload = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["created_by", "created_at"]),
        ]

    def __str__(self):
        return self.title
`,
    },
    {
      path: join(productDir, "services.py"),
      content: `from .models import ${pascal}Request


def create_${snake}_request(*, organization, created_by, title, input_payload=None):
    # TODO(product): Decide first whether this product can be solved with
    # deterministic code, classic ML/DL, or a low-cost model before adding any
    # external AI provider call.
    # TODO(api-key): Route future provider calls through a dedicated service
    # module and configure keys through environment secrets only.
    return ${pascal}Request.objects.create(
        organization=organization,
        created_by=created_by,
        title=title,
        input_payload=input_payload or {},
    )
`,
    },
    {
      path: join(productDir, "serializers.py"),
      content: `from rest_framework import serializers

from .models import ${pascal}Request
from .services import create_${snake}_request


class ${pascal}RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ${pascal}Request
        fields = (
            "id",
            "organization",
            "created_by",
            "title",
            "status",
            "input_payload",
            "result_payload",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ${pascal}CreateSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    title = serializers.CharField(max_length=240)
    input_payload = serializers.JSONField(required=False)

    def create(self, validated_data):
        return create_${snake}_request(
            organization=validated_data["organization"],
            created_by=validated_data["created_by"],
            title=validated_data["title"],
            input_payload=validated_data.get("input_payload", {}),
        )
`,
    },
    {
      path: join(productDir, "views.py"),
      content: `from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response

from apps.audit.services import log_audit_event
from apps.organizations.models import MembershipStatus, Organization
from apps.organizations.permissions import require_membership

from .models import ${pascal}Request
from .serializers import ${pascal}CreateSerializer, ${pascal}RequestSerializer


def get_member_organization(user, organization_id):
    organization = get_object_or_404(
        Organization.objects.filter(
            memberships__user=user,
            memberships__status=MembershipStatus.ACTIVE,
        ).distinct(),
        id=organization_id,
    )
    require_membership(user, organization)
    return organization


class ${pascal}RequestListCreateView(generics.ListCreateAPIView):
    queryset = ${pascal}Request.objects.none()
    serializer_class = ${pascal}RequestSerializer
    throttle_scope = "product_write"

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="organization_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ],
        request=${pascal}CreateSerializer,
        responses=${pascal}RequestSerializer,
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(request=${pascal}CreateSerializer, responses=${pascal}RequestSerializer)
    def post(self, request, *args, **kwargs):
        serializer = ${pascal}CreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = get_member_organization(
            request.user,
            serializer.validated_data["organization_id"],
        )
        product_request = serializer.save(organization=organization, created_by=request.user)
        log_audit_event(
            action="products.${snake}.request.created",
            organization=organization,
            request=request,
            category="products",
            target_entity_type="${snake}_request",
            target_entity_id=product_request.id,
        )
        return Response(
            ${pascal}RequestSerializer(product_request).data,
            status=status.HTTP_201_CREATED,
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ${pascal}Request.objects.none()

        organization = get_member_organization(
            self.request.user,
            self.request.query_params.get("organization_id"),
        )
        return ${pascal}Request.objects.filter(organization=organization).select_related(
            "created_by"
        )
`,
    },
    {
      path: join(productDir, "urls.py"),
      content: `from django.urls import path

from .views import ${pascal}RequestListCreateView

urlpatterns = [
    path("requests/", ${pascal}RequestListCreateView.as_view(), name="${slug}-requests"),
]
`,
    },
    {
      path: join(productDir, "admin.py"),
      content: `from django.contrib import admin

from .models import ${pascal}Request


@admin.register(${pascal}Request)
class ${pascal}RequestAdmin(admin.ModelAdmin):
    list_display = ("organization", "title", "status", "created_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "organization__name", "created_by__email")
`,
    },
    {
      path: join(productDir, "migrations", "__init__.py"),
      content: "\n",
    },
    {
      path: frontendPage,
      content: `import { FlaskConical } from "lucide-react";

import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/StateBlock";

export function ${pascal}Page() {
  return (
    <>
      <PageHeader eyebrow="Product" icon={FlaskConical} title="${title}" />
      <section className="tool-panel">
        <EmptyState title="Connect this product module to the generated backend endpoint." />
      </section>
    </>
  );
}
`,
    },
  ];
}

function writeProductFiles(files, options) {
  for (const file of files) {
    const exists = existsSync(file.path);
    const action = exists ? "exists" : "create";
    console.log(`${options.dryRun ? "would " : ""}${action}: ${file.path}`);
    if (options.dryRun) {
      continue;
    }
    if (exists && !options.force) {
      throw new Error(`Refusing to overwrite existing file: ${file.path}`);
    }
    mkdirSync(dirname(file.path), { recursive: true });
    writeFileSync(file.path, file.content);
  }
}

try {
  const options = parseArgs(process.argv.slice(2));
  requireValidSlug(options.slug);
  const files = productFiles(options);
  writeProductFiles(files, options);
  if (!options.dryRun) {
    console.log("Next: register the Django app, include its URL, run makemigrations, and add UI routing.");
  }
} catch (error) {
  console.error(error.message);
  process.exit(1);
}

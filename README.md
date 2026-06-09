# SaaS Core Template

Reusable API-first foundation for one-click and no-click AI-powered SaaS products.

This repository is intended to become the shared starting point for future nano-SaaS,
micro-SaaS, mini-SaaS, and full SaaS products. Product-specific logic should be added
on top of the core platform, not baked into the template.

## Current Phase

Current scaffold:

- backend dependency manifests and Django project baseline
- frontend dependency manifest and Vite baseline
- Docker and Docker Compose structure
- environment examples
- documentation placeholders
- CI workflow skeleton
- custom user model, JWT auth, organizations, memberships, and role permissions
- email verification and optional Google sign-in behind backend auth services
- billing skeleton with seeded plans, subscriptions, Stripe placeholders, and webhook verification
- organization-scoped plan entitlements with safe boolean feature flags
- usage tracking foundation with plan-limit enforcement services
- integrations skeleton with provider registry, encrypted credentials, connected accounts, and sync logs
- AI skeleton with provider registry, task profiles, model policies, execution planning,
  prompt templates, structured output validation, and call tracking
- reports/jobs/notifications foundation for queued and scheduled report workflows,
  secure artifact downloads, and delivery logs

See [CHANGELOG.txt](CHANGELOG.txt) for the phase-by-phase implementation history.

## Standard Stack

- Backend: Django + Django REST Framework
- API docs: OpenAPI via drf-spectacular
- Database: PostgreSQL
- Async jobs: Celery + Redis
- Frontend: React + TypeScript + Vite
- Billing: Stripe Checkout, Customer Portal, and webhooks
- AI: backend-only provider abstraction, OpenAI as default
- Storage: S3-compatible object storage
- Production target: AWS ECS Fargate, RDS, ElastiCache, S3, CloudFront, Secrets Manager
- Local development: Docker Compose

## Repository Layout

```text
backend/    Django API, apps, services, tests, and backend configuration
frontend/   React application shell, shared UI, API client, and frontend tests
docs/       Architecture, security, product workflow, deployment, and testing notes
deploy/     Docker, Docker Compose, and AWS deployment notes
postman/    Postman collection and environment examples
.github/    CI workflow definitions
```

## Local Setup

Docker Desktop is recommended for local development.

1. Copy environment examples:

   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

2. Start the local stack after Docker is installed:

   ```bash
   docker compose --env-file .env -f deploy/docker-compose.yml up --build
   ```

3. Expected local URLs:

   - Backend API health: http://localhost:8000/api/v1/health/
   - Swagger UI: http://localhost:8000/api/v1/docs/
   - Redoc: http://localhost:8000/api/v1/redoc/
   - Frontend: http://localhost:5173/

The first implementation phases will expand the backend apps and frontend shell.

For browser-based cloud IDEs such as Replit, use the same environment examples,
run PostgreSQL and Redis as external services, expose backend/frontend ports, and
keep secrets in the platform secret store. Replit is an optional development
environment, not a production dependency or replacement for the AWS target.

Generate and verify frontend API route types from the backend OpenAPI contract:

```bash
npm run api:types
npm run api:types:check
```

## Development Rules

- Keep the backend API-first.
- Route all AI and third-party API calls through backend service layers.
- Keep core modules generic and product-agnostic.
- Enforce organization permissions and usage limits server-side.
- Mock external APIs, Stripe, email, and AI providers in automated tests.
- Do not commit secrets, provider credentials, tokens, or real customer data.
- Do not add scraping or crawling utilities to the core template.

## Implemented Backend Endpoints

- `GET /api/v1/health/`
- `POST /api/v1/auth/register/`
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/refresh/`
- `POST /api/v1/auth/logout/`
- `GET/PATCH /api/v1/auth/me/`
- `POST /api/v1/auth/email/verify/`
- `POST /api/v1/auth/email/verification/resend/`
- `GET /api/v1/auth/social/google/status/`
- `POST /api/v1/auth/social/google/`
- `POST /api/v1/auth/password/recover/`
- `POST /api/v1/auth/password/reset/`
- `POST /api/v1/auth/password/change/`
- `GET/POST /api/v1/organizations/`
- `GET/PATCH/DELETE /api/v1/organizations/{id}/`
- `GET /api/v1/organizations/{id}/members/`
- `POST /api/v1/organizations/{id}/invite-member/`
- `GET /api/v1/billing/plans/`
- `GET /api/v1/billing/subscription/?organization_id=...`
- `GET /api/v1/billing/entitlements/?organization_id=...`
- `POST /api/v1/billing/checkout/`
- `POST /api/v1/billing/customer-portal/`
- `POST /api/v1/billing/webhooks/stripe/`
- `GET /api/v1/usage/summary/?organization_id=...`
- `GET /api/v1/integrations/providers/`
- `GET /api/v1/integrations/accounts/?organization_id=...`
- `POST /api/v1/integrations/{provider_slug}/connect/`
- `POST /api/v1/integrations/{account_id}/disconnect/`
- `POST /api/v1/integrations/{account_id}/reconnect/`
- `GET /api/v1/integrations/{account_id}/sync-logs/`
- `GET /api/v1/ai/providers/`
- `GET /api/v1/ai/prompt-templates/`
- `GET /api/v1/ai/task-profiles/`
- `GET /api/v1/ai/model-policies/?task_key=...`
- `POST /api/v1/ai/execution-plan/`
- `GET /api/v1/ai/decision-logs/?organization_id=...`
- `GET /api/v1/ai/call-logs/?organization_id=...`
- `GET /api/v1/jobs/?organization_id=...`
- `GET/POST /api/v1/jobs/schedules/`
- `GET /api/v1/jobs/schedules/{id}/runs/`
- `POST /api/v1/jobs/schedules/{id}/run/`
- `POST /api/v1/jobs/schedules/{id}/pause/`
- `POST /api/v1/jobs/schedules/{id}/resume/`
- `GET /api/v1/reports/templates/`
- `GET/POST /api/v1/reports/`
- `GET /api/v1/reports/{id}/`
- `GET /api/v1/reports/{id}/artifacts/`
- `GET /api/v1/reports/{id}/artifacts/{artifact_id}/download/`
- `GET/POST /api/v1/notifications/preferences/`
- `GET /api/v1/notifications/delivery-logs/?organization_id=...`
- `GET/POST /api/v1/privacy/exports/`
- `GET/POST /api/v1/privacy/deletion-requests/`
- `POST /api/v1/privacy/deletion-requests/{id}/execute/`

## External Accounts

Stripe, OpenAI, AWS, SES/Resend, and product-specific provider accounts are not
required for the current backend core phase. When those phases start, follow
[docs/external-accounts.md](docs/external-accounts.md) and keep all credentials
out of the repository.

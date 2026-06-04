# AGENTS.md

Repository-level instructions for Codex and other AI coding agents working on this repository.

This repository is a reusable SaaS Core Template. It is not a single product. Keep all core code generic, API-first, secure by default, and easy to reuse across future one-click and no-click SaaS products.

## 1. Always read these documents first

Before planning, coding, reviewing, or refactoring, read the relevant documents below:

- `README.md`
- `CHANGELOG.txt`
- `docs/architecture.md`
- `docs/api-conventions.md`
- `docs/security.md`
- `docs/testing.md`
- `docs/product-patterns.md`
- `docs/create-new-saas-from-template.md`
- `docs/review-quality-gates-and-definition-of-done.md`
- `EXTERNAL_SETUP_CHECKLIST.md`

If a requested task conflicts with these instructions, follow the more specific project document. If the conflict affects security, billing, data isolation, credentials, or production deployment, stop and report the conflict before making changes.

## 2. Project purpose and boundaries

The goal of this repository is to provide a reusable foundation for multiple SaaS products under one umbrella brand.

The template must support:

- API-first backend architecture.
- Reusable frontend shell and design system.
- Auth, organizations/workspaces, memberships, roles, and permissions.
- Stripe billing and usage-limit enforcement.
- Integration framework for official or reputable provider APIs.
- Backend-only AI provider abstraction and cost tracking.
- Reports, async jobs, scheduled jobs, notifications, audit logs, and legal/disclaimer foundations.
- One-click product pattern: input/connect -> job -> analysis -> result/report.
- No-click product pattern: setup -> schedule -> sync/analyze -> alert/report.

Do not turn this repository into a specific SaaS product unless the user explicitly asks for that. Product-specific modules should be added under a product namespace and must not pollute the core template.

## 3. Standard stack

Default stack for this repository:

- Backend: Django + Django REST Framework.
- Database: PostgreSQL.
- Async jobs: Celery + Redis.
- API documentation: OpenAPI via drf-spectacular, Swagger UI, and Redoc.
- Frontend: React + TypeScript + Vite.
- Billing: Stripe Checkout, Stripe Customer Portal, and Stripe webhooks.
- AI: backend-only provider abstraction; OpenAI as default placeholder; Anthropic/Gemini optional through abstraction.
- Storage: S3-compatible object storage for reports, exports, and generated files.
- Local development: Docker Compose.
- Production target: AWS ECS Fargate or similar container runtime, RDS PostgreSQL, ElastiCache Redis, S3, CloudFront, Secrets Manager/SSM, CloudWatch, Route 53/ACM where applicable.

Do not introduce Kubernetes, microservices, GraphQL, multi-cloud abstractions, complex event streaming, or heavy ML/DL dependencies unless there is a concrete product need and the user explicitly approves the added complexity.

## 4. Architecture rules

### Backend

- Keep the backend API-first. The frontend, mobile clients, desktop clients, and automations must consume the same REST API.
- Keep business logic out of views/controllers where practical. Use serializers, services, selectors, tasks, clients, validators, and domain modules.
- All organization-scoped data must enforce membership and role permissions server-side.
- All paid or limited actions must enforce subscription status, feature flags, and usage limits server-side.
- All long-running operations must create a request/job/run record and expose status/result endpoints.
- Keep API response shapes stable and documented in OpenAPI.
- Use migrations for schema changes. Do not modify historical migrations unless explicitly asked and safe for the current project phase.
- Add explicit indexes for high-volume or lookup-heavy tables such as jobs, reports, usage, audit logs, credentials, provider accounts, and webhook events.

### Frontend

- Keep the UI minimal, flat, airy, predictable, and reusable across products.
- Reuse the shared dashboard shell, design tokens, components, API client, forms, tables, cards, loading states, empty states, errors, and success states.
- Avoid complex animations, over-designed pages, and multiple competing primary actions.
- Do not call AI providers, Stripe secret APIs, or third-party provider APIs directly from the frontend.
- Keep frontend API types aligned with backend OpenAPI contracts where practical.

### Product modules

- Add product-specific backend code under `backend/apps/products/<product_name>/` or the existing product namespace.
- Add product-specific frontend pages/components without breaking the common shell and design system.
- Product modules must call core billing, usage, AI, reports, jobs, notifications, audit, and integrations through reusable service layers.
- Product modules must not bypass organization permissions, feature flags, usage limits, audit logging, or provider abstractions.

## 5. External APIs and integrations

- Use official APIs or reputable third-party APIs whenever possible.
- Do not add generic scraping or crawling utilities to the core template.
- Every external provider must be behind a replaceable service/client layer.
- Views/controllers must not call HTTP libraries directly for provider APIs.
- Store provider credentials securely and never expose secrets or tokens to the frontend.
- Support token refresh, expired-token detection, reconnect, disconnect, provider health checks, rate-limit handling, retry state, and sync logs where relevant.
- Mock all external APIs in automated tests.

## 6. AI and model selection rules

- Frontend must never call AI providers directly.
- Product modules must call AI only through the backend AI decision/model policy layer.
- First check whether the task can be solved without AI:
  1. deterministic code/rules,
  2. classic algorithms or lightweight ML,
  3. optional local small model,
  4. low-cost LLM,
  5. standard LLM,
  6. advanced LLM,
  7. human review for high-risk cases.
- Do not default to expensive models.
- Track provider, model, tokens, estimated cost, latency, organization, user, related entity, prompt version, status, cache usage, and errors.
- Prefer structured outputs for downstream logic. Validate AI outputs before storing or displaying them.
- Do not allow frontend input to force model escalation, override internal AI policies, or spoof expected run volume/cost.
- Add AI disclaimers where AI-generated output is displayed or included in reports.

## 7. Billing, usage, and Stripe rules

- Use Stripe Checkout for subscription purchase and Stripe Customer Portal for billing management.
- Stripe webhook signature verification is mandatory.
- Webhook handling must be idempotent by Stripe event ID.
- Never store raw card data.
- Store only safe Stripe identifiers and billing metadata needed by the app.
- Inactive paid subscriptions must not retain paid feature access unless explicitly intended and tested.
- Feature flags and usage limits must be enforced in backend services/endpoints, not only hidden in the UI.
- Usage reservation/check-and-record logic must be concurrency-safe for quota-sensitive actions.
- Billing redirect URLs must be validated against an allowlist.

## 8. Security and privacy rules

- Never commit secrets, API keys, provider credentials, tokens, real customer data, or private provider details.
- Keep `.env.example` files safe and placeholder-only.
- Use separate `DJANGO_SECRET_KEY` and integration credential encryption keys.
- Validate JSON payload sizes on expensive or user-controlled endpoints.
- Apply throttling to auth, billing actions, expensive AI/report actions, and product write endpoints.
- Restrict sensitive operational logs to owner/admin or staff-only access as appropriate.
- Avoid leaking prompts, model policies, provider configuration, internal cost thresholds, raw report payloads, stack traces, credential metadata, or audit-heavy details to regular users.
- Add audit logs for security-sensitive actions: auth events, billing events, integration changes, AI execution planning, report requests, notification preference changes, admin actions, and data deletion flows.
- Prefer safe defaults in production settings: secure cookies, HTTPS, allowed hosts, CSRF trusted origins, CORS allowlist, security headers, JSON logs, and explicit environment variables.

## 9. Testing and quality gates

Tests are part of the template, not optional cleanup.

Use focused tests for functions that:

- make decisions,
- enforce permissions,
- enforce organization scoping,
- enforce billing or usage limits,
- change state,
- validate input,
- calculate cost or usage,
- handle retries,
- interact with Stripe, AI, email, storage, or external providers,
- create audit logs,
- generate reports or artifacts.

Backend testing should cover services, validators, serializers, permissions, endpoints, webhooks, usage limits, AI policy decisions, provider failures, job retry logic, audit logs, and legal/disclaimer acceptance.

Frontend testing should cover auth flows, protected routing, API error rendering, forms, dashboard shell behavior, billing states, integration states, report flows, notification settings, and core navigation.

Mock Stripe, AI providers, email providers, storage, and third-party APIs in automated tests.

Before marking work complete, run the strongest available checks for the changed area. Prefer the repository's root scripts when available:

```bash
npm run backend:lint
npm run backend:check
npm run backend:migrations:check
npm run frontend:lint
npm run frontend:typecheck
npm run frontend:test
npm run frontend:build
npm run release:check
```

If a command is unavailable, inspect `package.json`, backend tooling config, and frontend tooling config to find the correct equivalent. Do not invent successful test results. Report exactly what was run and what could not be run.

## 10. Docker, AWS, and deployment rules

- Docker should support local development, CI consistency, and production application images.
- Local Docker Compose should model backend, frontend, PostgreSQL, Redis, Celery worker, and scheduler/beat where possible.
- Production stateful services should be managed services: RDS for PostgreSQL, ElastiCache for Redis, S3 for object storage, Secrets Manager/SSM for secrets, CloudWatch for logs/metrics.
- Backend API, Celery workers, and scheduled workers should be containerized as separate runtime services when needed.
- Frontend production hosting should use S3 + CloudFront or AWS Amplify Hosting unless a product-specific reason exists.
- Do not run PostgreSQL or Redis in production containers except for temporary internal test environments.
- Prefer IAM roles and GitHub OIDC over long-lived AWS access keys.
- Keep deployment documentation updated when environment variables, secrets, infrastructure assumptions, or service boundaries change.

## 11. Documentation and changelog rules

Update documentation when behavior, commands, APIs, environment variables, security posture, setup steps, or productization workflow changes.

Update `CHANGELOG.txt` at the end of every implementation phase or significant remediation phase. Entries must stay factual:

- what changed,
- what was verified,
- what remains external or not configured.

Do not record secrets, API keys, credentials, real customer data, or private provider details in the changelog.

Keep product-specific work out of the template changelog unless it affects reusable template functionality.

## 12. Review policy

Before performing a code review, read `docs/review-quality-gates-and-definition-of-done.md`.

Do not perform open-ended reviews that generate endless fix cycles. Classify every finding as one of:

- BLOCKER,
- CRITICAL,
- MAJOR,
- MINOR,
- NIT.

Only BLOCKER, CRITICAL, and MAJOR findings are mandatory before merge/release. MINOR and NIT findings should be listed separately as backlog unless the user explicitly asks to fix them now.

During review, focus on:

- requirement compliance,
- security and data isolation,
- organization scoping and role permissions,
- billing, feature flag, and usage enforcement,
- API contracts and OpenAPI correctness,
- Stripe webhook safety,
- AI cost/policy guardrails,
- external provider abstraction,
- async job/report correctness,
- tests and quality gates,
- production configuration safety.

Ignore pure style preferences, speculative edge cases, broad rewrites, and optional refactors unless they block a requirement or create real production risk.

Stop the review/fix loop when:

- all in-scope acceptance criteria are implemented or explicitly deferred,
- required automated checks pass or failures are documented,
- no BLOCKER, CRITICAL, or MAJOR findings remain,
- remaining MINOR/NIT items are listed as backlog.

## 13. Standard response format for coding tasks

When completing a coding task, report:

1. Summary of changes.
2. Files changed.
3. Tests/checks run and results.
4. Known limitations or intentionally deferred items.
5. Whether any follow-up is required.

Do not claim that tests passed if they were not run. Do not hide skipped checks. Do not say external services are configured unless real credentials/accounts were provided and verified.

## 14. Standard response format for reviews

When performing a review, use this format:

```text
Review scope
- Documents/policies read:
- Code areas reviewed:
- Commands/checks run:

Mandatory findings
- BLOCKER:
- CRITICAL:
- MAJOR:

Backlog findings
- MINOR:
- NIT:

Requirement compliance summary
- Implemented:
- Partially implemented:
- Missing:
- Deferred:

Stop-rule status
- Ready to merge/release: yes/no
- Reason:
```

Do not request another review cycle unless mandatory findings remain.

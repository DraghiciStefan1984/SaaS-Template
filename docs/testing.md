# Testing

The template uses pragmatic TDD for critical logic and lightweight workflow tests for important user journeys.

## Test When Logic Makes Decisions

Any function that makes a decision, applies a rule, changes state, validates input, calculates cost or usage,
enforces permissions, or interacts with an external service must have focused tests.

## Backend

- Unit tests for services, validators, permissions, and helpers
- API tests for endpoints, organization scoping, errors, pagination, and filters
- Mocked integration tests for Stripe, AI, email, and external provider clients
- Workflow tests for one-click and no-click flows

Current backend coverage includes registration, login, logout, suspended account
blocking, organization scoping, role permissions, seeded billing plans, free
subscriptions, Stripe webhook signature verification, usage limit enforcement,
integration credential encryption, integration role permissions, OAuth placeholder
behavior, seeded AI providers, structured AI output validation, and AI call logging
when provider keys are missing. Coverage also includes AI execution planning,
strategy selection, decision logs, report request creation, job retry state,
generic multi-format report rendering, notification preferences, delivery logs,
and user-scoped in-app read state.
Coverage also includes token-based password reset and refresh-token revocation,
scheduled workflow permissions/execution/dispatch, integration reconnect, and
role-gated report artifact downloads.
Coverage also includes signed email verification/resend, mocked Google identity
login, organization-scoped safe entitlements, deploy requirements for optional
Google login, and generated OpenAPI route type drift checks.
Coverage also includes signed organization invitation send/resend/cancel/accept
and invitation email ownership checks.
Negative-path coverage includes Google identity claim validation, invitation
reuse/tampering, configured Stripe checkout/portal mocks, Stripe subscription
lifecycle webhooks, AI policy selection and escalation guards, provider
credential failures, scheduled workflow guards, report retry exhaustion,
artifact storage boundaries, notification provider failures, and privacy
handling for in-app notifications.
Integration coverage also verifies customer-managed provider discovery,
encrypted BYOK storage, provider-declared credential fields, platform-managed
provider rejection, role gates, disconnect deletion, reconnect, and
organization-specific AI provider readiness.

## Frontend

- Component tests for shared components and important states
- Mocked API tests for request errors, refresh/retry behavior, auth lifecycle,
  recovery/reset, invitation acceptance, reports, notifications, billing,
  profile/security, privacy deletion, settings, integrations, and AI planning
- Playwright smoke tests for key navigation

## Coverage Gates

- `npm run backend:coverage` runs backend line/branch coverage and requires at
  least 90% total coverage.
- `npm run frontend:coverage` runs Vitest V8 coverage and requires at least 50%
  statements/branches/lines and 40% functions.
- `npm run release:check` includes both coverage gates.
- Backend tests use fast in-memory SQLite by default for local development.
  Set `TEST_DATABASE_URL` to a PostgreSQL connection URL and run
  `npm run backend:test:postgres-concurrency` to verify database-specific
  concurrency semantics. The command recreates its isolated test database so
  data migrations and test ordering cannot affect the result.

## CI Gates

- backend lint
- backend tests with the 90% coverage gate
- a dedicated PostgreSQL job for the concurrent usage-reservation test
- migration checks
- frontend lint
- frontend typecheck
- frontend tests with coverage thresholds
- smoke tests on important branches
- the deploy workflow runs `npm run release:check` before deploy validation and
  image builds

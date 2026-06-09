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
placeholder report generation, notification preferences, and delivery logs.
Coverage also includes token-based password reset and refresh-token revocation,
scheduled workflow permissions/execution/dispatch, integration reconnect, and
role-gated report artifact downloads.
Coverage also includes signed email verification/resend, mocked Google identity
login, organization-scoped safe entitlements, deploy requirements for optional
Google login, and generated OpenAPI route type drift checks.

## Frontend

- Component tests for shared components and important states
- API mocking with MSW
- Playwright smoke tests for key navigation

## CI Gates

- backend lint
- backend tests
- migration checks
- frontend lint
- frontend typecheck
- frontend tests
- smoke tests on important branches

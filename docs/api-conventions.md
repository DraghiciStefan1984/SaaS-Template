# API Conventions

All APIs should use `/api/v1/` as the initial version prefix.

## Standards

- Use resource-oriented plural nouns.
- Use `GET` for reads, `POST` for creation and explicit actions, `PATCH` for partial updates, and `DELETE` for deletions.
- Return a job or request ID for long-running operations.
- Enforce organization membership and role permissions on scoped endpoints.
- Enforce billing and usage limits server-side.
- Include every endpoint in OpenAPI documentation.
- Use consistent pagination, filtering, ordering, and search.

## Initial Documentation URLs

- Swagger UI: `/api/v1/docs/`
- Redoc: `/api/v1/redoc/`
- Schema: `/api/v1/schema/`

## Implemented Core Areas

- Auth: registration, login, refresh, logout, current user profile, email
  verification/resend, optional Google identity login, password recovery request,
  token-based password reset, password change
- Organizations: organization CRUD, members list, invite placeholder
- Billing: public plan list, organization subscription, safe boolean entitlements,
  checkout placeholder, customer portal placeholder, Stripe webhook endpoint
- Usage: organization usage summary
- Integrations: provider registry, connected accounts, disconnect/reconnect
  actions, sync logs
- AI: provider registry, prompt template list, organization-scoped call logs
- Jobs and reports: report requests, secure artifact download, job history,
  scheduled report creation/actions/run history
- Privacy: export requests, deletion requests, owner/requester-scoped deletion
  execution

## Frontend Contract Types

The frontend keeps a small typed API wrapper for request/response models and a
generated route/method inventory derived from drf-spectacular OpenAPI:

```bash
npm run api:types
npm run api:types:check
```

`api:types:check` is part of `release:check`; API changes must regenerate
`frontend/src/lib/api-paths.generated.ts`.

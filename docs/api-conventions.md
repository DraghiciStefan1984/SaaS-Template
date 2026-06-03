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

- Auth: registration, login, refresh, logout, current user profile
- Organizations: organization CRUD, members list, invite placeholder
- Billing: public plan list, organization subscription, checkout placeholder,
  customer portal placeholder, Stripe webhook endpoint
- Usage: organization usage summary
- Integrations: provider registry, connected accounts, disconnect action, sync logs
- AI: provider registry, prompt template list, organization-scoped call logs

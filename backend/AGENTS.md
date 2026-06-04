# Backend Agent Instructions

These instructions apply to files under `backend/`.

Before changing backend code, read the root `AGENTS.md` and the relevant docs in `docs/`.

## Backend boundaries

- Keep the backend API-first and product-agnostic unless the task is explicitly product-specific.
- Put reusable platform logic in the existing core apps: accounts, organizations, billing, usage, integrations, ai, reports, jobs, notifications, privacy, audit, and common.
- Put product-specific backend code under `backend/apps/products/<product_name>/`.
- Product code must call reusable service layers for billing, usage, AI, integrations, reports, jobs, notifications, privacy, and audit.
- Views must stay thin. Business logic belongs in services, validators, permissions, or model-level helpers.

## Mandatory safety checks

For every backend change, verify the affected area for:

- organization scoping and membership permissions;
- owner/admin/member role behavior;
- suspended user behavior where auth is involved;
- backend-side billing feature gates and usage limits;
- Stripe webhook signature verification and idempotency where billing is involved;
- credential/token secrecy and encrypted storage for integrations;
- AI decision-layer use instead of direct provider calls;
- object-only JSON validation for dict-like payloads;
- audit logs for security-sensitive actions;
- privacy export/anonymization hooks when adding customer data models.

## Required checks

Prefer root scripts:

```bash
npm run backend:lint
npm run backend:check
npm run backend:migrations:check
npm run backend:test
```

For release-level backend work also run:

```bash
npm run release:check
```

Report any command that could not be run and why. Do not claim tests passed if they were skipped.

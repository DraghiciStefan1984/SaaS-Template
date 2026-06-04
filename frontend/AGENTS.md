# Frontend Agent Instructions

These instructions apply to files under `frontend/`.

Before changing frontend code, read the root `AGENTS.md` and the relevant docs in `docs/`.

## Frontend boundaries

- Keep the UI consistent with the shared SaaS template: minimal, flat, airy, predictable, and reusable.
- Reuse the shared dashboard shell, typed API client, forms, tables, cards, loading states, empty states, error states, and success states.
- Do not call AI providers, Stripe secret APIs, storage providers, or third-party provider APIs directly from the frontend.
- Treat backend API contracts as the source of truth.
- Do not store refresh tokens in browser-accessible storage. Session restoration should rely on the backend refresh-cookie flow.
- Do not expose admin-only provider IDs, internal AI decision details, raw payloads, stack traces, or sensitive audit data to regular members.

## Required checks

Prefer root scripts:

```bash
npm run frontend:lint
npm run frontend:typecheck
npm run frontend:test
npm run frontend:build
```

When UI flows change materially, run or update Playwright smoke tests if the browser dependency is available.

Report any command that could not be run and why. Do not claim tests passed if they were skipped.

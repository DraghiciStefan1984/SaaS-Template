# Acceptance Criteria Template

Use this file for every new template phase or product-specific SaaS module.

## Feature / phase

Name:
Owner:
Status: draft | in progress | review | done | deferred

## Requirement map

| ID | Requirement | Source document | Status | Implementation reference | Tests | Notes |
|---|---|---|---|---|---|---|
| REQ-001 |  |  | missing |  |  |  |
| REQ-002 |  |  | missing |  |  |  |
| REQ-003 |  |  | missing |  |  |  |

Status values:

- implemented
- partially implemented
- missing
- intentionally deferred
- not applicable

## API contract checklist

- [ ] Endpoints use `/api/v1/`.
- [ ] Endpoints are organization-scoped where required.
- [ ] Membership and role permissions are enforced server-side.
- [ ] Paid features are gated server-side.
- [ ] Usage limits are checked and recorded server-side.
- [ ] Validation errors are structured and renderable by the frontend.
- [ ] Long-running operations return job/request IDs and status endpoints.
- [ ] OpenAPI schema includes the new/changed endpoints.
- [ ] Frontend API types/client are updated where needed.

## Security and privacy checklist

- [ ] No secrets are committed.
- [ ] No raw provider credentials are returned to the frontend.
- [ ] Sensitive payloads are hidden from regular members.
- [ ] Audit events are created for sensitive actions.
- [ ] Customer data models are covered by privacy export/anonymization hooks.
- [ ] Logs avoid tokens, credentials, raw prompts, raw payloads, and stack traces.
- [ ] Destructive actions are permission-checked and auditable.

## Billing / usage checklist

- [ ] Feature flag exists where needed.
- [ ] Usage metric exists where needed.
- [ ] Backend enforces access before expensive work starts.
- [ ] Quota-sensitive actions use concurrency-safe check-and-record logic.
- [ ] Inactive subscriptions do not retain paid access unintentionally.

## AI checklist

- [ ] Deterministic or non-AI solution was considered first.
- [ ] AI calls go through the backend AI decision layer.
- [ ] Model escalation is policy-driven, not user-controlled.
- [ ] Tokens/cost/latency/provider/model/status are logged.
- [ ] Structured outputs are validated before storage/display.
- [ ] AI disclaimers are shown where relevant.

## Test plan

Backend:

- [ ] service tests
- [ ] serializer/validator tests
- [ ] permission/scoping tests
- [ ] API contract tests
- [ ] webhook/provider failure tests where relevant
- [ ] privacy/audit tests where relevant

Frontend:

- [ ] component tests
- [ ] API error rendering tests
- [ ] protected route/navigation tests
- [ ] billing/integration/report state tests where relevant
- [ ] E2E smoke test where relevant

## Definition of done

- [ ] Acceptance criteria implemented or explicitly deferred.
- [ ] Required checks pass or failures are documented.
- [ ] No BLOCKER, CRITICAL, or MAJOR review findings remain.
- [ ] MINOR/NIT findings are listed as backlog.
- [ ] README/docs/changelog updated if behavior changed.

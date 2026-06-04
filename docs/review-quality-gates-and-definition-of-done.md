# Review, Quality Gates, and Definition of Done

This document defines how Codex and other AI agents should review this SaaS Core Template without creating an endless review -> fix -> review loop.

The purpose is not to find unlimited possible improvements. The purpose is to decide whether the current implementation is safe, correct, aligned with the specification, and ready for the next phase.

## 1. Core principle

A review is complete when all mandatory risks are addressed.

A feature, phase, or release candidate is not required to be perfect. It must be:

- compliant with the in-scope requirements,
- secure enough for the current phase,
- covered by relevant tests,
- aligned with the architecture rules,
- free of known BLOCKER, CRITICAL, or MAJOR issues,
- explicit about deferred MINOR/NIT backlog items.

Do not continue reviewing indefinitely after the mandatory issues are resolved.

## 2. Review inputs

Before reviewing, read the relevant files:

- `AGENTS.md`
- `README.md`
- `CHANGELOG.txt`
- `docs/architecture.md`
- `docs/api-conventions.md`
- `docs/security.md`
- `docs/testing.md`
- `docs/product-patterns.md`
- `docs/create-new-saas-from-template.md`
- `EXTERNAL_SETUP_CHECKLIST.md`
- the original SaaS Core Template specification, if available in the task context

For product-specific tasks, also read the product-specific specification, acceptance criteria, API contract, and implementation notes.

## 3. Review types

Use the smallest useful review type. Do not default to a full repository review.

### 3.1 Requirements compliance review

Goal: verify that the implementation matches the specification.

Check:

- required backend modules exist or are intentionally deferred,
- required frontend flows exist or are intentionally deferred,
- API endpoints match documented contracts,
- one-click and no-click patterns are supported where in scope,
- product-specific logic does not leak into the core template,
- no scraping/crawling utilities are added to the core template,
- AI and provider calls go through backend abstractions.

### 3.2 Security and data isolation review

Goal: find issues that could expose data, bypass permissions, or weaken production safety.

Check:

- organization scoping,
- membership and role permissions,
- suspended account behavior,
- sensitive log access,
- credential storage,
- secret handling,
- payload validation,
- throttling,
- audit logging,
- CORS/CSRF/allowed hosts/cookie/security-header assumptions,
- data deletion/destructive behavior.

### 3.3 Billing and usage review

Goal: find ways users could bypass paid features, plan limits, or Stripe state.

Check:

- server-side feature gates,
- server-side usage limits,
- inactive subscription fallback behavior,
- Stripe webhook signature verification,
- webhook idempotency,
- checkout/customer portal redirect allowlists,
- concurrency safety for quota-sensitive actions,
- frontend does not become the source of truth for billing access.

### 3.4 API contract review

Goal: ensure frontend-facing API behavior is stable and documented.

Check:

- endpoints appear in OpenAPI,
- response shapes match frontend expectations,
- validation errors are structured and renderable,
- pagination/filtering/sorting are consistent where relevant,
- auth and permission failures return appropriate status codes,
- long-running actions return job/request identifiers and status endpoints.

### 3.5 Testing and quality gate review

Goal: verify that important logic has automated coverage and commands pass.

Check:

- backend lint,
- Django system check,
- migration check,
- OpenAPI validation,
- backend tests,
- frontend lint,
- frontend typecheck,
- frontend tests,
- frontend build,
- e2e smoke tests where available,
- release check where available.

### 3.6 Production readiness review

Goal: verify deployment and external setup assumptions.

Check:

- Docker files and Compose config,
- environment examples,
- AWS deployment notes,
- Secrets Manager/SSM assumptions,
- RDS/ElastiCache/S3/CloudWatch assumptions,
- frontend hosting assumptions,
- external account checklist,
- observability configuration,
- no real secrets in repo.

## 4. Severity levels

Every finding must be classified using exactly one severity.

### BLOCKER

Must be fixed immediately. The work cannot be merged, released, or considered complete.

Examples:

- App cannot start or core flow is broken.
- Tests/checks fail because of the change.
- Migration is broken or unsafe for the current phase.
- Authentication is unusable.
- Organization isolation is clearly broken.
- Billing access can be bypassed for paid features.
- Stripe webhook handling is unsafe or non-idempotent.
- Secrets, real credentials, tokens, or private data are committed.
- Frontend directly calls AI/provider secret APIs.
- A destructive operation can execute without clear authorization or safe default.

### CRITICAL

Must be fixed before merge/release. The system may run, but there is serious security, billing, data, or production risk.

Examples:

- Regular users can access sensitive operational logs.
- Suspended users can continue authenticated use.
- Prompt templates, model policies, credentials, or raw report payloads leak to normal users.
- Usage limits are checked only in the frontend.
- Stripe redirect URLs are unvalidated.
- Public input can force expensive AI model escalation.
- Credential encryption keys are missing, reused incorrectly, or unsafe.
- External provider calls bypass service/client abstraction.
- Critical logic has no tests.

### MAJOR

Should be fixed before merge/release unless explicitly deferred by the user. It affects correctness, maintainability, security posture, or requirement compliance.

Examples:

- Required acceptance criterion is partially implemented.
- API response shape does not match frontend needs.
- OpenAPI schema is incomplete for new endpoints.
- Important permission edge case is untested.
- Important provider failure/rate-limit path is not handled.
- Job retry/error state is ambiguous.
- Report generation path lacks a reliable status/result model.
- Frontend does not handle backend validation errors for important forms.
- Changelog/docs are missing for significant behavior changes.

### MINOR

Should be tracked in backlog. Usually not mandatory before merge/release.

Examples:

- Small duplication that does not create correctness risk.
- Non-critical UI copy issue.
- Optional helper refactor.
- Missing convenience abstraction.
- Extra test coverage for simple framework glue.
- Minor docs clarification.
- Small performance improvement not needed at current scale.

### NIT

Optional polish only. Never block merge/release unless the user explicitly asks for polish.

Examples:

- Naming preference.
- Formatting preference already covered by formatter/linter.
- Alternative component organization with no practical impact.
- Comment wording.
- Pure aesthetic preference.

## 5. Mandatory fix policy

Fix immediately:

- BLOCKER,
- CRITICAL,
- MAJOR unless explicitly deferred.

Do not fix immediately by default:

- MINOR,
- NIT.

Instead, put MINOR and NIT findings in a backlog section.

This policy is intended to stop endless AI review loops. A new review cycle should not be requested just because MINOR/NIT items exist.

## 6. Definition of Done for an implementation task

A task is done when:

1. The implementation matches the in-scope requirement.
2. Product-specific logic has not been added to the reusable core unless requested.
3. Backend business logic is in services/tasks/serializers/validators/clients where practical, not buried in views.
4. Organization scoping and role permissions are enforced server-side for scoped data.
5. Billing feature flags and usage limits are enforced server-side for paid/limited actions.
6. External providers, AI providers, email, storage, and Stripe are accessed through abstractions and are mocked in tests.
7. API endpoints are documented in OpenAPI where applicable.
8. Frontend states cover loading, success, validation error, backend error, empty state, and disabled submit states where relevant.
9. Relevant tests have been added or updated.
10. Required checks pass, or failures are explicitly documented with reason.
11. Documentation and changelog are updated when behavior/setup/API/security changed.
12. No BLOCKER, CRITICAL, or MAJOR findings remain.
13. MINOR/NIT findings, if any, are listed as backlog.

## 7. Definition of Done for a template phase

A phase is done when:

1. The phase deliverables are implemented or explicitly deferred.
2. The repository still works as a reusable template, not a product-specific app.
3. API-first architecture is preserved.
4. Core modules remain generic and extension-friendly.
5. Backend and frontend checks pass for the affected areas.
6. Release-level checks pass when the phase is release-candidate level.
7. `CHANGELOG.txt` records:
   - what changed,
   - what was verified,
   - what remains external/not configured.
8. External services that are not configured are clearly listed as placeholders.
9. No mandatory review findings remain.

## 8. Definition of Done for a product created from the template

A new SaaS product created from this template is done enough for initial launch only when:

1. Product requirements are converted into acceptance criteria.
2. Product-specific modules are isolated under product namespaces.
3. Core auth, organization, billing, usage, reports, jobs, notifications, audit, and integration patterns are reused.
4. Product-specific provider clients use the integration framework.
5. Product-specific AI use follows the AI cost ladder and model policy layer.
6. Product-specific plan limits are configured and tested.
7. Main user journey has workflow/e2e smoke coverage.
8. OpenAPI/Postman examples are updated.
9. Stripe test-mode flow is verified before live mode.
10. Production deployment checklist is complete.
11. No BLOCKER, CRITICAL, or MAJOR findings remain.

## 9. Quality gate checklist

Use the strongest available commands in the repository. Prefer root aliases if they exist.

### Backend gates

- Lint passes.
- Django system check passes.
- Migration check passes.
- OpenAPI validation passes.
- Backend tests pass.
- Security-sensitive paths have focused tests.
- External services are mocked.

Typical commands:

```bash
npm run backend:lint
npm run backend:check
npm run backend:migrations:check
```

Run full backend tests using the repository's configured command. If `npm run release:check` exists, it should include this.

### Frontend gates

- Lint passes.
- Typecheck passes.
- Unit tests pass.
- Production build passes.
- E2E smoke tests pass where available.

Typical commands:

```bash
npm run frontend:lint
npm run frontend:typecheck
npm run frontend:test
npm run frontend:build
```

### Release gate

For a release candidate, prefer:

```bash
npm run release:check
```

If this command exists, it should be the default final verification command because it is expected to combine productization checks, backend checks, OpenAPI validation, tests, frontend checks, and build validation.

## 10. Requirement compliance matrix

For large tasks, create or update a requirement matrix before reviewing code.

Use this format:

```text
REQ-001: <requirement>
Status: implemented | partially implemented | missing | deferred | not applicable
Evidence: <files/endpoints/tests>
Mandatory before release: yes | no
Notes: <short explanation>
```

Do not mark a requirement as implemented without code evidence or test evidence.

## 11. Standard Codex review prompt

Use this prompt instead of asking for an open-ended full review:

```text
Review the current implementation according to AGENTS.md and docs/review-quality-gates-and-definition-of-done.md.

Before reviewing, read:
- AGENTS.md
- README.md
- CHANGELOG.txt
- docs/architecture.md
- docs/api-conventions.md
- docs/security.md
- docs/testing.md
- docs/product-patterns.md
- EXTERNAL_SETUP_CHECKLIST.md

Scope:
- Check requirement compliance for the current task/phase.
- Check security, organization scoping, billing/usage enforcement, API contracts, tests, and production safety.
- Classify every finding as BLOCKER, CRITICAL, MAJOR, MINOR, or NIT.
- Only BLOCKER, CRITICAL, and MAJOR are mandatory fixes.
- Put MINOR and NIT into backlog.
- Do not suggest broad refactors, style-only changes, or speculative improvements unless they block a requirement or create real production risk.
- Stop when no BLOCKER, CRITICAL, or MAJOR findings remain.

Output format:
1. Review scope
2. Mandatory findings
3. Backlog findings
4. Requirement compliance summary
5. Commands/checks run
6. Stop-rule status
```

## 12. Standard Codex fix prompt

When fixing review findings, use this prompt:

```text
Fix only the BLOCKER, CRITICAL, and MAJOR findings from the previous review.

Do not fix MINOR or NIT backlog items unless they are directly required by a mandatory fix.
Do not introduce broad refactors.
Keep the architecture aligned with AGENTS.md.
Add or update focused tests for every mandatory fix.
Run the relevant checks and report exactly what passed or failed.
```

## 13. Stop rule

The review/fix cycle must stop when:

- no BLOCKER findings remain,
- no CRITICAL findings remain,
- no MAJOR findings remain unless explicitly deferred,
- relevant automated checks pass or known failures are documented,
- remaining MINOR/NIT items are listed as backlog.

At that point, the correct next action is not another general review. The correct next action is to merge, release, or start a new scoped task.

## 14. What not to do

Do not:

- ask for repeated full reviews after every minor fix,
- treat MINOR/NIT findings as mandatory,
- rewrite working architecture for subjective preference,
- add product-specific logic to the core template without explicit instruction,
- add scraping/crawling utilities to the core template,
- call external APIs directly from views or frontend code,
- expose secrets, tokens, prompts, model policies, or sensitive logs,
- claim tests passed without running them,
- hide skipped checks,
- configure live external services unless credentials and explicit instructions are provided.

## 15. Recommended final review answer format

```text
Review scope
- Documents read:
- Code areas reviewed:
- Commands/checks run:

Mandatory findings
- BLOCKER: none | list
- CRITICAL: none | list
- MAJOR: none | list

Backlog findings
- MINOR: none | list
- NIT: none | list

Requirement compliance
- Implemented:
- Partially implemented:
- Missing:
- Deferred/not applicable:

Stop-rule status
- Ready: yes/no
- Reason:
```

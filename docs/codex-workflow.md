# Codex Workflow for SaaS Core Template

This document defines the recommended way to use Codex on this repository without creating an endless review/fix cycle.

## 1. Golden rule

Do not ask for open-ended reviews such as "review everything" or "find all problems".

Use bounded tasks:

- plan first;
- implement one coherent change;
- run the strongest relevant checks;
- review only against the policy;
- fix only BLOCKER, CRITICAL, and MAJOR findings immediately;
- move MINOR and NIT items to backlog.

## 2. First prompt in a new Codex thread

Use this when starting a non-trivial task:

```text
Read AGENTS.md and the relevant docs before making changes.

Task:
<describe the task>

First produce a short implementation plan. Do not edit files yet.
Identify:
- files likely to change;
- risks around auth, organization scoping, billing/usage, AI cost, privacy, and API contracts;
- tests/checks that should be run.
```

After the plan looks good, continue with:

```text
Implement the approved plan.
Keep the change small and focused.
Run the relevant checks.
Report changed files, checks run, limitations, and deferred items.
```

## 3. Review prompt

Use this instead of "do a full code review":

```text
Review the current implementation according to AGENTS.md and docs/review-quality-gates-and-definition-of-done.md.

Scope:
- requirement compliance for the current task;
- security and data isolation;
- organization scoping and role permissions;
- billing, feature flags, and usage enforcement;
- API contracts and OpenAPI correctness;
- Stripe webhook safety if billing was touched;
- AI cost/policy guardrails if AI was touched;
- tests and quality gates.

Classify every finding as BLOCKER, CRITICAL, MAJOR, MINOR, or NIT.
Only BLOCKER, CRITICAL, and MAJOR are mandatory fixes.
List MINOR and NIT separately as backlog.
Do not request another review cycle unless mandatory findings remain.
```

## 4. Remediation prompt

Use this after Codex returns review findings:

```text
Fix only the BLOCKER, CRITICAL, and MAJOR findings from the previous review.
Do not fix MINOR or NIT items unless they are required to solve a mandatory issue.
After changes, run the relevant checks and summarize what remains in backlog.
```

## 5. Stop rule

Stop the implementation/review loop when:

- all in-scope acceptance criteria are implemented or explicitly deferred;
- required checks pass, or failures are documented with a clear reason;
- there are no BLOCKER, CRITICAL, or MAJOR findings;
- remaining MINOR/NIT items are in backlog.

At that point, the task is done for the current phase.

## 6. Recommended checks by task type

### Backend-only change

```bash
npm run backend:lint
npm run backend:check
npm run backend:migrations:check
npm run backend:test
```

### Frontend-only change

```bash
npm run frontend:lint
npm run frontend:typecheck
npm run frontend:test
npm run frontend:build
```

### Cross-stack, security, billing, auth, privacy, AI, or product scaffold change

```bash
npm run release:check
```

### Docker/deployment change

```bash
npm run docker:config
npm run deploy:check
```

Run Docker build/up only when Docker Desktop or a Docker-capable environment is available.

## 7. Codex cloud/local setup script

Use this as the Codex environment setup script where setup scripts are supported:

```bash
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-dev.txt
npm install --prefix frontend
```

Use this as a lightweight maintenance script after dependency files change:

```bash
python -m pip install -r backend/requirements-dev.txt
npm install --prefix frontend
```

## 8. What not to upload or commit

Do not include local/generated artifacts in GitHub or ZIPs used for review:

- `backend/.venv/`
- `frontend/node_modules/`
- `__pycache__/`
- `.ruff_cache/`
- `frontend/dist/`
- `backend/db.sqlite3`
- local logs
- local `.env` files

These files make Codex slower, can break Linux-based checks, and add noise to code search.

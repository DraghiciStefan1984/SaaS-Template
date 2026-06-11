# Architecture

The template is an API-first SaaS platform foundation.

## Core Principles

- Backend owns all business logic, AI calls, provider API calls, billing checks, and usage enforcement.
- Frontend is a client of the backend API.
- Core modules stay reusable and product-agnostic.
- Product-specific modules extend the core through service layers and app namespaces.
- Slow work runs through Celery jobs.
- Production stateful services are managed AWS services.
- Billing and usage are shared platform modules. Product modules should call the
  usage service before expensive actions and route billing changes through the
  billing service layer.

## Product Extension Pattern

Future products should add:

- product-specific backend app
- provider client implementation
- AI prompt and structured output schema
- report generator
- frontend feature page
- dashboard widgets
- plan limits and feature flags

## Current Core Modules

- `accounts`: custom user model, JWT auth, email verification, and optional
  Google identity-token login
- `organizations`: workspaces, memberships, and role checks
- `billing`: plans, subscriptions, Stripe checkout/customer portal/webhook
  skeleton, and safe organization entitlement projection
- `usage`: usage records and plan-limit enforcement
- `integrations`: safe customer-configurable provider registry, connected
  accounts, encrypted organization credentials, BYOK resolution, and sync logs
- `ai`: provider registry, task profiles, model policies, execution decisions, prompts,
  call logs, result cache
- `jobs`: queued/background workflow state, attempts, retries, and errors
- `reports`: report templates, report requests, generated artifacts, and generation hooks
- `notifications`: notification preferences and delivery logs behind provider abstractions

## AI Decision Layer

Product code should not call AI providers directly. It should request an execution
plan from the AI service layer, then use the returned strategy:

- `deterministic` for rules, formulas, and simple code paths
- `classic_ml` for statistics, forecasting, clustering, scoring, and table analysis
- `local_model` for small local models when the product explicitly adds them
- `low_cost_llm`, `standard_llm`, or `advanced_llm` when language/reasoning quality
  justifies a provider call
- `human_review` for high-risk workflows

This keeps model choice configurable per task/profile/plan while preserving a
single audit trail for cost, fallback, and risk decisions.

Organization-owned AI API keys can satisfy provider configuration for that
organization. Product/provider clients must resolve them only in backend
services. Platform-managed credentials remain environment/secret-manager
configuration and must never be added to the customer integration registry.

## Background Workflow Pattern

Long-running product actions should create a domain entity first, then a `JobRun`.
The Celery task updates the domain entity, creates artifacts/logs, and records
retry/failure state on the job. Report generation follows this pattern and is the
reference implementation for future no-click SaaS workflows.

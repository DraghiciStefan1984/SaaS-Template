# Integrations and AI

The template now includes generic foundations for external integrations and AI
provider usage. These modules are intentionally provider-agnostic and do not call
real third-party APIs until credentials and provider clients are added.

## Integrations

Core models:

- `IntegrationProvider`: provider registry entry with auth type, scopes, status,
  feature flags, and config metadata.
- `IntegrationAccount`: organization-scoped connected account/resource.
- `IntegrationCredential`: encrypted credential payload attached to an account.
- `IntegrationSyncLog`: sync attempt history, external request IDs, retry state,
  rate-limit metadata, and error tracking.

Implemented endpoints:

- `GET /api/v1/integrations/providers/`
- `GET /api/v1/integrations/accounts/?organization_id=...`
- `POST /api/v1/integrations/{provider_slug}/connect/`
- `POST /api/v1/integrations/{account_id}/disconnect/`
- `POST /api/v1/integrations/{account_id}/reconnect/`
- `GET /api/v1/integrations/{account_id}/sync-logs/`

Current behavior:

- API-key providers can be connected using an encrypted credential payload.
- Disconnected API-key and credential-free accounts can be explicitly
  reconnected. Replacement credentials are encrypted and never returned.
- OAuth providers return a descriptive `503` until OAuth client settings and a
  provider-specific OAuth client are implemented.
- Credentials are never returned by API serializers.
- Product modules must use provider clients/service layers instead of calling
  HTTP libraries directly from views.

## AI

Core models:

- `AIProvider`: provider registry for OpenAI, Anthropic, Gemini, and future
  product-specific AI providers.
- `AITaskProfile`: reusable task profile that defines allowed strategies,
  expected volume, risk posture, cost threshold, and default strategy.
- `AIModelPolicy`: configurable mapping from a task profile to a strategy,
  provider/model, plan override, fallback strategy, and execution rules.
- `AIModelDecisionLog`: organization-scoped audit trail for selected strategy,
  provider/model, fallback, constraints, and decision reason.
- `PromptTemplate`: versioned prompt templates with optional structured output
  schema.
- `AICallLog`: organization/user/provider/model tracking for status, latency,
  tokens, estimated cost, request hash, response payload, and errors.
- `AIResultCache`: reusable cache foundation for safe AI result reuse.

Implemented endpoints:

- `GET /api/v1/ai/providers/`
- `GET /api/v1/ai/prompt-templates/`
- `GET /api/v1/ai/task-profiles/`
- `GET /api/v1/ai/model-policies/?task_key=...`
- `POST /api/v1/ai/execution-plan/`
- `GET /api/v1/ai/decision-logs/?organization_id=...`
- `GET /api/v1/ai/call-logs/?organization_id=...`

Reusable services:

- `provider_configuration_status(...)`
- `ensure_provider_configured(...)`
- `latest_prompt_template(...)`
- `build_request_hash(...)`
- `validate_structured_output(...)`
- `select_ai_execution_plan(...)`
- `run_ai_task(...)`
- `run_ai_prompt(...)`

Current behavior:

- OpenAI, Anthropic, and Gemini providers are seeded.
- Default task profiles are seeded for recurring reports, table analysis,
  document extraction, support assistants, and high-risk advice.
- Execution planning follows the AI Cost Ladder: deterministic code first,
  then classic ML/DL, local models, low-cost LLMs, standard LLMs, advanced LLMs,
  and human review for high-risk cases.
- `select_ai_execution_plan(...)` returns strategy, provider/model when needed,
  fallback metadata, configuration status, and a decision log.
- Provider configuration status reports missing API keys until environment values
  exist.
- `run_ai_prompt(...)` logs failed attempts when the provider key is missing.
- Real provider execution is intentionally not implemented in the core template.
  Product endpoints should call this service after selecting a provider and
  prompt, then a provider-specific client can be plugged in.

Example product flow:

1. Product service receives a request for a report, forecast, extraction, or assistant response.
2. Product service calls `select_ai_execution_plan(...)` or `run_ai_task(...)`.
3. If the selected strategy is deterministic/classic/local, the product-specific
   executor handles the work without a paid LLM call.
4. If the selected strategy is an LLM tier, the backend AI provider adapter handles
   the provider call after API keys and clients are configured.
5. Decision logs and call logs remain organization-scoped for audit, cost control,
   and debugging.

## External Accounts

No external accounts are required for this phase.

Needed later:

- OpenAI project API key for real OpenAI calls.
- Anthropic key only if a product needs Anthropic.
- Gemini key only if a product needs Gemini.
- OAuth client IDs/secrets per external provider.
- API keys per API-key provider.

Store production secrets in AWS Secrets Manager or equivalent, not repository
files.

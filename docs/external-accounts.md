# External Accounts and API Keys

This template must run without real external accounts during early development.
When an external provider is needed, add credentials through environment variables
or a production secret manager, never through committed files.

## Required Later

### Stripe

Needed when billing is implemented.

- Create a Stripe account.
- Use test mode first.
- Create products and prices for Starter, Pro, and Agency plans.
- Configure webhook endpoints per environment.
- Store the webhook signing secret separately from API keys.

Environment variables:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_STARTER`
- `STRIPE_PRICE_PRO`
- `STRIPE_PRICE_AGENCY`

Current code already includes Stripe checkout/customer portal/webhook placeholders.
Until the account, price IDs, and webhook secret exist, billing actions return a
descriptive `503` response instead of attempting live Stripe calls.

### OpenAI

Needed when real AI workflows are implemented.

- Create an OpenAI platform account.
- Create a project for this SaaS factory or for each product.
- Create a project API key.
- Set budget/usage limits before production.

Environment variables:

- `OPENAI_API_KEY`
- `DEFAULT_AI_PROVIDER`
- `DEFAULT_AI_MODEL`

Current code seeds the OpenAI provider and reports `not_configured` until
`OPENAI_API_KEY` exists. Real provider execution remains behind the backend AI
service layer. The AI execution planner works without external accounts and can
select deterministic, classic ML/DL, local-model, low-cost LLM, standard LLM,
advanced LLM, or human-review strategies before any provider call is attempted.

### Anthropic / Gemini

Optional fallback providers. Do not create accounts until a product needs them.

Environment variables:

- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`

Current code seeds Anthropic and Gemini provider registry entries, but does not
call either provider until a product explicitly needs them.

### Product Integration Providers

Needed when a product requires a specific external API.

- OAuth providers need provider-specific client IDs, client secrets, redirect
  URLs, scopes, and token refresh rules.
- API-key providers need a secure API key storage and rotation process.
- Provider clients must live behind the integrations service layer.

Current code can store API-key credentials encrypted for a connected integration
account. OAuth connect attempts return a descriptive `503` until OAuth client
settings and provider-specific exchange logic exist.

Organization owners/admins can manage customer-owned credentials from the
dashboard integrations page. The reusable registry currently includes OpenAI,
Anthropic, and Gemini API-key forms plus a disabled-until-configured Slack OAuth
entry. Stored credential values are write-only and encrypted.

Do not add platform Stripe billing keys, AWS credentials, email-provider keys,
Sentry DSNs, Django secrets, or deployment credentials through this panel. Those
belong to the SaaS operator and must stay in environment-specific secret
management. A future product that analyzes a customer's Stripe account should
use a separate Stripe Connect/OAuth provider integration, not the platform
billing secret key.

### Google Login

Optional for products that want social sign-in.

- Create a Google Cloud project and OAuth consent screen.
- Create a Web application OAuth Client ID.
- Add every frontend origin to Authorized JavaScript origins.
- Set `GOOGLE_OAUTH_CLIENT_ID` in the backend environment.

The browser receives a Google identity credential and sends it to the backend.
The backend verifies signature, audience, issuer, expiry, and verified email
plus the short-lived login nonce before creating or authenticating the user. No
Google Client Secret is required for this ID-token flow.

### AWS

Needed when staging or production deployment begins.

- Create an AWS account.
- Enable MFA on root.
- Use IAM Identity Center or a dedicated admin identity.
- Create cost budgets and alerts.
- Use managed services for production state: RDS, ElastiCache, S3, ECS Fargate,
  CloudFront, Secrets Manager, CloudWatch.

Environment variables for local/staging tooling:

- `AWS_REGION`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_STORAGE_BUCKET_NAME`

Production secrets should live in AWS Secrets Manager, not `.env` files.

### Email Provider

Needed when invites, report delivery, password reset, and alerts send real email.

Recommended options:

- AWS SES for AWS-native production.
- Resend for simpler setup and staging.

Local development should continue using `EMAIL_PROVIDER=console` until real
delivery is required. Password reset, email verification, and organization
invitation emails already use the configured Django email backend, so they appear
in the local console backend. Notification delivery logs and the in-app
notification center work without a provider account. SES/Resend/Postmark should
be configured behind the Django email/service layer when production email is needed.

## Implementation Rule

Whenever code reaches a provider that is not connected yet, leave a descriptive
comment and route the future call through a service layer. Do not call provider SDKs
directly from views or frontend code.

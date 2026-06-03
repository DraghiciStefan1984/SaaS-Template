# External Setup Checklist

This file lists the accounts, API keys, cloud services, and local tooling needed
to move the SaaS template from local release candidate to real deployed products.
Do not commit real secrets. Store real values in local `.env` files, AWS Secrets
Manager / SSM Parameter Store, and GitHub environment secrets.

## Needed Now

### Docker Desktop

Purpose:
- Run the full local stack with backend, frontend, PostgreSQL, Redis, Celery
  worker, and Celery beat.
- Validate `deploy/docker-compose.yml`.

Install:
- Docker Desktop for Windows.

Account/API key:
- No API key is required for local Docker.
- Docker Hub account is optional. If we deploy images to AWS ECR, Docker Hub is
  not required.

Commands after install:
```bash
npm run docker:config
npm run docker:build
npm run docker:up
```

### GitHub

Purpose:
- Host the repository.
- Run CI and the manual deploy workflow.
- Store deploy secrets and environment variables.

Needed:
- GitHub repository.
- GitHub Actions enabled.
- Environments: `staging`, later `production`.

GitHub secrets/vars to add later:
- `DJANGO_SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `OPENAI_API_KEY`
- `SENTRY_DSN`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `CORS_ALLOWED_ORIGINS`
- `FRONTEND_BASE_URL`
- `AWS_REGION`
- `DEFAULT_AI_PROVIDER`
- `EMAIL_PROVIDER`
- `DEFAULT_FROM_EMAIL`
- `AWS_STORAGE_BUCKET_NAME`

## Needed For AWS Deployment

### AWS Account

Purpose:
- Host backend/frontend/runtime.
- Managed database, cache, object storage, secrets, logs.

Recommended services:
- ECR for Docker images.
- ECS Fargate or App Runner for app services.
- RDS PostgreSQL for database.
- ElastiCache Redis for cache/Celery broker.
- S3 for reports, exports, generated files.
- Secrets Manager or SSM Parameter Store for secrets.
- CloudWatch for logs.
- IAM roles / OIDC for GitHub deploys.
- Route 53 or another DNS provider for domains.
- ACM for TLS certificates.

Values to prepare:
- `AWS_REGION`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `AWS_STORAGE_BUCKET_NAME`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `CORS_ALLOWED_ORIGINS`
- `FRONTEND_BASE_URL`

Important:
- Prefer IAM roles and GitHub OIDC over long-lived AWS access keys.
- If access keys are temporarily needed, keep them out of the repo.

### Domain/DNS

Purpose:
- Public URLs for frontend and backend.

Needed:
- Domain name.
- DNS provider: Route 53, Cloudflare, or similar.
- TLS certificate via AWS ACM if using AWS load balancers/App Runner.

Example target values:
- Frontend: `https://app.example.com`
- API: `https://api.example.com/api/v1`

Frontend env:
- `VITE_API_BASE_URL`
- `VITE_PUBLIC_SITE_URL`

Backend env:
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `CORS_ALLOWED_ORIGINS`
- `FRONTEND_BASE_URL`

## Needed For Billing

### Stripe

Purpose:
- Subscriptions, checkout, customer portal, webhooks.

Start with:
- Stripe account.
- Test mode enabled.
- Products/prices for plans.
- Local or staging webhook endpoint.

Keys/values:
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_FREE`
- `STRIPE_PRICE_STARTER`
- `STRIPE_PRICE_PRO`
- `STRIPE_PRICE_AGENCY`

Where:
- Local: `backend/.env`
- AWS: Secrets Manager / SSM / GitHub environment secrets

Important:
- Use test keys first.
- Add live keys only after the full billing workflow is verified.

## Needed For AI Features

### OpenAI

Purpose:
- Real AI provider calls when a SaaS needs LLM output.
- The template can run without this key; it currently has AI decision/planning
  logic and placeholders.

Keys/values:
- `OPENAI_API_KEY`
- `DEFAULT_AI_PROVIDER=openai`
- `DEFAULT_AI_MODEL`

Usage rule:
- Do not use an advanced model by default.
- First check whether the product can use deterministic logic, classic ML/DL, or
  a low-cost model.
- Use advanced models only when the value justifies the cost and simpler methods
  are not reliable enough.

### Optional AI Providers

Only create these if a concrete SaaS needs them:
- Anthropic: `ANTHROPIC_API_KEY`
- Google Gemini: `GEMINI_API_KEY`
- Other provider-specific keys per product

## Needed For Email

Choose one provider before production email delivery:
- AWS SES
- Resend
- Postmark
- SendGrid

Current local default:
- `EMAIL_PROVIDER=console`

Production/staging values:
- `EMAIL_PROVIDER`
- `DEFAULT_FROM_EMAIL`
- `AWS_SES_REGION` if using SES

Optional provider-specific values:
- `RESEND_API_KEY`
- `POSTMARK_SERVER_TOKEN`
- `SENDGRID_API_KEY`

These optional keys are not wired into code yet. Add them only when choosing the
email provider implementation.

## Needed For Observability

### Sentry

Purpose:
- Error monitoring and release tracking.

Values:
- `SENTRY_DSN`
- `SENTRY_TRACES_SAMPLE_RATE`
- `ENVIRONMENT`
- `DEPLOY_VERSION`

Recommended:
- `LOG_FORMAT=json` in staging/production.
- `DEPLOY_VERSION` should be the git SHA, release tag, or image tag.

### AWS CloudWatch

Purpose:
- Runtime logs from ECS/App Runner.

No app API key is needed.
Use AWS runtime configuration and JSON logs.

## Optional Integrations Per Product

Only create these accounts/apps when a SaaS actually needs them:

### Google APIs

Possible use:
- Google Sheets import/export.
- Google Drive Docs/Sheets workflows.

Needed:
- Google Cloud project.
- OAuth consent screen.
- OAuth client ID/secret.
- Enabled APIs per product.

Possible env values:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

Not wired into production code yet.

### Slack

Possible use:
- Notifications, alerts, workspace actions.

Needed:
- Slack app.
- OAuth client ID/secret.
- Bot scopes.

Possible env values:
- `SLACK_CLIENT_ID`
- `SLACK_CLIENT_SECRET`
- `SLACK_SIGNING_SECRET`

Not wired into production code yet.

### Product-Specific APIs

Examples:
- CRM APIs
- Analytics APIs
- Accounting APIs
- Scraping/data providers
- Payment/tax providers

Rule:
- Add each provider behind a backend service layer.
- Add descriptive TODO comments where the account/API key is still missing.
- Do not call provider SDKs directly from frontend or product views.

## Local Tooling And Libraries

Already represented in the repo:
- Python/Django backend dependencies in `backend/requirements.txt`
- Backend dev/test dependencies in `backend/requirements-dev.txt`
- Angular is not currently used; frontend is React/Vite.
- Frontend dependencies in `frontend/package.json`
- PostgreSQL and Redis are expected through Docker Compose.

Install locally:
- Docker Desktop
- Node.js 22
- Python 3.13
- Git

Optional CLI tools:
- AWS CLI
- GitHub CLI
- Stripe CLI for local webhook testing

Useful commands:
```bash
npm run demo:prepare
npm run release:check
npm run deploy:check
npm run deploy:check:full
npm run product:scaffold:dry-run
```

## Priority Order

1. Install Docker Desktop.
2. Create or connect the GitHub repository.
3. Create AWS account/resources for staging.
4. Configure domain/DNS and TLS.
5. Create Stripe account and test-mode products/prices.
6. Create OpenAI API key only when we test real AI provider calls.
7. Choose email provider before real notifications/invites.
8. Add Sentry before production launch.
9. Add Google/Slack/other integrations only per SaaS need.

## What Not To Do

- Do not commit real `.env` files.
- Do not commit API keys in examples.
- Do not add live Stripe keys before test billing works.
- Do not create OAuth apps for integrations that no product needs yet.
- Do not add advanced AI calls where deterministic code or classic ML/DL is
  enough.

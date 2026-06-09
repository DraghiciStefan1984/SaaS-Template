# Deployment

## Local Development

Use Docker Compose for local PostgreSQL, Redis, backend, frontend, Celery worker, and scheduler.

```bash
docker compose --env-file .env -f deploy/docker-compose.yml up --build
```

## Production Baseline

- ECS Fargate for backend API and workers
- RDS PostgreSQL
- ElastiCache Redis
- S3 for report artifacts and exports
- CloudFront plus S3 or Amplify Hosting for frontend
- Secrets Manager for secrets
- CloudWatch for logs
- SES or provider abstraction for email

## AWS Production Sequence

1. Create separate staging and production environments, AWS budgets, MFA, and
   IAM Identity Center access.
2. Create ECR repositories and use GitHub OIDC/IAM roles for image publishing.
3. Provision RDS PostgreSQL, ElastiCache Redis, and S3 with private networking,
   encryption, backups, and environment-specific resources.
4. Store Django, integration, provider, and billing secrets in Secrets Manager
   or SSM. Do not pass long-lived AWS access keys to application containers.
5. Deploy backend API, Celery worker, and Celery Beat as separate ECS Fargate
   services/task definitions using the same versioned application image.
6. Run migrations as an explicit one-off task before releasing the new API task
   definition.
7. Host the frontend through S3 + CloudFront or Amplify and configure API CORS,
   CSRF origins, secure refresh cookies, Route 53, and ACM certificates.
8. Send JSON logs to CloudWatch, configure alarms, add Sentry DSN/release, and
   run `npm run deploy:check:full` before production traffic.

The deployment workflow remains a provider-ready skeleton until real AWS
resource identifiers and GitHub environment configuration exist.

## Replit / Cloud IDE

Replit may be used for short-lived development or demonstrations. Use managed
PostgreSQL/Redis, platform secrets, and public port configuration; run the same
checks and Docker images where supported. Do not treat the Replit filesystem as
durable storage and do not replace the AWS production baseline with it.

See `docs/external-accounts.md` before connecting Stripe, OpenAI, AWS, SES, or
any product-specific provider API.

## Deployment Rule

Do not deploy product-specific secrets, provider tokens, Stripe keys, or AI keys in repository files.

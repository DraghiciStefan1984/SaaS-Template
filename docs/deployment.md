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

See `docs/external-accounts.md` before connecting Stripe, OpenAI, AWS, SES, or
any product-specific provider API.

## Deployment Rule

Do not deploy product-specific secrets, provider tokens, Stripe keys, or AI keys in repository files.

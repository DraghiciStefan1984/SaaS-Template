# AWS Deployment Notes

Recommended production baseline:

- Backend API: ECS Fargate service
- Celery worker: ECS Fargate service
- Scheduler/Celery Beat: ECS Fargate service or scheduled task
- PostgreSQL: Amazon RDS
- Redis: Amazon ElastiCache
- Frontend: S3 + CloudFront or AWS Amplify Hosting
- File storage: S3
- Secrets: AWS Secrets Manager with KMS
- Email: AWS SES or another provider behind the email service abstraction
- Logs and metrics: CloudWatch
- DNS and TLS: Route 53 and AWS Certificate Manager

Start with AWS Copilot CLI for simple ECS/Fargate deployments. Move to AWS CDK or
Terraform when infrastructure requirements become too complex for Copilot.

Do not run PostgreSQL or Redis in production containers for customer-facing
applications. Use managed AWS services for stateful infrastructure.


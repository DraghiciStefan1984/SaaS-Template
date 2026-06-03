# Security

Security defaults should be conservative from the first implementation.

## Rules

- Never commit secrets.
- Use encrypted storage or secure references for OAuth tokens and API keys.
- Verify Stripe and provider webhook signatures.
- Enforce organization-level permissions on scoped endpoints.
- Enforce plan and usage limits server-side.
- Use rate limiting for auth, AI, report generation, and external API-triggering endpoints.
- Do not leak stack traces, provider responses, tokens, or secrets in user-facing errors.
- Configure CORS explicitly in production.
- Store only necessary personal data.
- Add audit logs for security-sensitive actions.
- Do not store raw card data.
- Do not include generic scraping or crawling in the core template.


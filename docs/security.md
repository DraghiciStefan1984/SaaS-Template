# Security

Security defaults should be conservative from the first implementation.

## Rules

- Never commit secrets.
- Use encrypted storage or secure references for OAuth tokens and API keys.
- Restrict customer-managed credential changes to organization owners/admins,
  validate provider-declared credential fields, and never return stored values.
- Expose connected accounts to regular members only as safe connection-status
  summaries without external identifiers, scopes, or operational metadata.
- Keep Stripe billing, AWS, email, observability, Django, and deployment secrets
  platform-managed; do not expose them through customer credential forms.
- Verify Stripe and provider webhook signatures.
- Enforce organization-level permissions on scoped endpoints.
- Enforce plan and usage limits server-side.
- Use rate limiting for auth, AI, report generation, and external API-triggering endpoints.
- Keep password recovery responses generic, use signed one-time reset tokens, and
  revoke outstanding refresh tokens after password reset/change.
- Sign and expire email-verification links; do not trust an email address supplied
  by a social-login client without verifying the provider-issued identity token.
- Google sign-in uses the public OAuth Client ID only; provider tokens are verified
  in the backend, bound to a short-lived HttpOnly nonce cookie, and are never
  accepted as arbitrary email/profile payloads.
- Expose plan entitlements to members only as safe boolean flags. Keep internal
  billing configuration, costs, provider settings, and Stripe IDs restricted.
- Do not leak stack traces, provider responses, tokens, or secrets in user-facing errors.
- Configure CORS explicitly in production.
- Store only necessary personal data.
- Add audit logs for security-sensitive actions.
- Restrict report artifact downloads and scheduled workflow management to
  organization owners/admins and audit those actions.
- Do not store raw card data.
- Do not include generic scraping or crawling in the core template.

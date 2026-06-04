# Billing and Usage

The template includes a billing and usage skeleton that is safe to run without a
real Stripe account.

## Default Plans

The `billing` app seeds four configurable plans:

- Free
- Starter
- Pro
- Agency

Stripe price IDs are intentionally empty until a Stripe account and test products
exist. Add those values through environment variables or admin configuration in a
future billing phase.

## Subscription Foundation

Every new organization receives a Free subscription automatically when default
plans are available. This gives every organization a plan context from day one,
which lets product modules enforce usage limits even before paid billing is live.

## Usage Metrics

The `usage` app tracks usage by:

- organization
- subscription
- monthly period
- metric name
- quantity
- source
- product scope
- metadata

Reusable services:

- `check_and_record_usage(...)`
- `record_usage(...)`
- `get_usage_total(...)`
- `get_plan_limit(...)`
- `assert_within_usage_limit(...)`
- `usage_summary_for_organization(...)`

Any paid or limited product action should reserve usage with
`check_and_record_usage(...)` before doing expensive work. That service checks
the current plan limit and writes the usage record inside one transaction, which
avoids the old read-then-write race between `assert_within_usage_limit(...)` and
`record_usage(...)`.

Use `record_usage(...)` only for internal reconciliation or events that are not
quota-gated. `assert_within_usage_limit(...)` remains available for read-only UI
previews, but product endpoints should not pair it manually with
`record_usage(...)`.

## Stripe Placeholders

Implemented but not connected to a real account yet:

- `POST /api/v1/billing/checkout/`
- `POST /api/v1/billing/customer-portal/`
- `POST /api/v1/billing/webhooks/stripe/`

Until `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are configured, Stripe
actions return a descriptive `503` response.

Webhook signature verification is implemented and tested with a local test
secret. When a real Stripe account exists, configure per-environment webhook
secrets and price IDs before enabling live billing.

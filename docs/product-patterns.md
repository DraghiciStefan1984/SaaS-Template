# Product Patterns

## One-Click Pattern

Request -> job -> external APIs -> AI analysis -> structured result -> report.

Required pieces:

- request model
- async job
- status endpoint
- result endpoint
- usage and cost tracking
- report artifact
- history page

## No-Click Pattern

Setup -> schedule -> sync -> analyze -> notify.

Required pieces:

- monitor model
- schedule and timezone
- recipients and alert rules
- historical runs
- reports and alerts
- pause/resume controls

## Core Extraction Rule

When a useful pattern appears in two or three SaaS products, evaluate whether it belongs in the core template.


# Backend

Django + Django REST Framework API foundation.

## Dependency Files

- `requirements.txt`: runtime dependencies
- `requirements-dev.txt`: runtime plus test, lint, and developer tooling

## Native Setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

## Checks

```bash
pytest
ruff check .
python manage.py spectacular --file openapi.yaml
```

## App Boundaries

The future reusable apps should live under `backend/apps/`:

- accounts
- organizations
- billing
- usage
- integrations
- ai
- reports
- jobs
- notifications
- audit
- legal
- common

Product-specific apps should live under a product namespace, for example
`backend/apps/products/site_health/`.


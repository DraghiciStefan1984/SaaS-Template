from .base import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    **REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],  # noqa: F405
    "anon": "10000/hour",
    "user": "10000/hour",
    "auth": "10000/minute",
    "expensive_action": "10000/hour",
    "billing_action": "10000/hour",
    "product_write": "10000/hour",
}

MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE  # noqa: F405
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]

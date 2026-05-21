import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from config import settings


def init_sentry():
    """Initialize Sentry error tracking if SENTRY_DSN is configured."""
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint",
                    failed_request_status_codes=[400, 404, 422, 403, 406, 415],
                ),
                SqlalchemyIntegration(),
            ],
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            # We recommend adjusting this value in production.
            traces_sample_rate=0.1 if settings.app_env == "production" else 1.0,
            # Set profiles_sample_rate to 1.0 to profile 100%
            # of sampled transactions.
            # We recommend adjusting this value in production.
            profiles_sample_rate=0.1 if settings.app_env == "production" else 1.0,
            environment=settings.app_env,
        )
        print(f"Sentry initialized for environment: {settings.app_env}")
    else:
        print("Sentry DSN not configured, skipping Sentry initialization")

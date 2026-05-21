from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_connection_string: str

    # Admin
    fastapi_admin_secret_key: str
    admin_user: str
    admin_password: str

    # Frontend (Next.js app)
    # Comma-separated list of allowed origins for CORS.
    frontend_origins: str = "http://localhost:3000"

    # Application
    app_env: str = "development"
    debug: bool = False

    # Analytics
    ga_tracking_id: str | None = None

    # ipapi
    ipapi_secret_api_key: str | None = None

    # Sentry
    sentry_dsn: str | None = None

    @property
    def frontend_origins_list(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


settings = Settings()

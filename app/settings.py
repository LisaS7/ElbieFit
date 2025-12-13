from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(find_dotenv(), override=False)


class Settings(BaseSettings):
    PROJECT_NAME: str = "elbiefit"
    REGION: str = "eu-west-2"
    ENV: str = "dev"
    DDB_TABLE_NAME: str = "elbiefit-dev-table"
    model_config = SettingsConfigDict(env_file=None)

    # ──────────────────── Auth ─────────────────────

    DISABLE_AUTH_FOR_LOCAL_DEV: bool = False
    DEV_USER_SUB: str | None = None

    COGNITO_AUDIENCE: str = ""
    COGNITO_DOMAIN: str = ""
    COGNITO_REDIRECT_URI: str = ""
    COGNITO_ISSUER: str = ""

    # ──────────────────── Rate limiting ─────────────────────
    RATE_LIMIT_ENABLED: bool = True

    RATE_LIMIT_READ_PER_MIN: int = 120
    RATE_LIMIT_WRITE_PER_MIN: int = 30

    DEMO_RATE_LIMIT_READ_PER_MIN: int = 60
    DEMO_RATE_LIMIT_WRITE_PER_MIN: int = 15

    RATE_LIMIT_TTL_SECONDS: int = 600

    # Prefixes that should never be rate limited
    RATE_LIMIT_EXCLUDED_PREFIXES: tuple[str, ...] = (
        "/static",
        "/favicon.ico",
        "/robots.txt",
        "/health",
        "/meta",
    )

    # Demo
    DEMO_SESSION_COOKIE_NAME: str = "demo_session_id"

    # ─────────────────────────────────────────

    def cognito_base_url(self) -> str:
        return f"https://{self.COGNITO_DOMAIN}.auth.{self.REGION}.amazoncognito.com"

    def auth_url(self) -> str:
        return f"{self.cognito_base_url()}/oauth2/authorize"

    def token_url(self) -> str:
        return f"{self.cognito_base_url()}/oauth2/token"


settings = Settings()

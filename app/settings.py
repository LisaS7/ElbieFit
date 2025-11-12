from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(find_dotenv(), override=False)


class Settings(BaseSettings):
    PROJECT_NAME: str
    REGION: str
    ENV: str
    TABLE_NAME: str
    COGNITO_AUDIENCE: str
    COGNITO_DOMAIN: str
    COGNITO_REDIRECT_URI: str
    COGNITO_ISSUER: str

    model_config = SettingsConfigDict(env_file=None)


settings = Settings()

from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(find_dotenv(), override=False)


class Settings(BaseSettings):
    PROJECT_NAME: str = "elbiefit"
    REGION: str = "eu-west-2"
    ENV: str = "dev"
    DDB_TABLE_NAME: str = "elbiefit-dev-table"
    COGNITO_AUDIENCE: str = ""
    COGNITO_DOMAIN: str = ""
    COGNITO_REDIRECT_URI: str = ""
    COGNITO_ISSUER: str = ""

    model_config = SettingsConfigDict(env_file=None)


settings = Settings()

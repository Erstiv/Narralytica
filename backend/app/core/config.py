from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://narralytica:changeme_in_production@localhost:5433/narralytica"
    gemini_api_key: str = ""
    secret_key: str = "dev-secret-key"
    environment: str = "development"
    media_dir: str = "/app/media"

    model_config = {"env_file": ".env"}


settings = Settings()

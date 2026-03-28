from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://narralytica:changeme_in_production@localhost:5433/narralytica"
    gemini_api_key: str = ""
    secret_key: str = "dev-secret-key"
    environment: str = "development"
    media_dir: str = "/app/media"

    # Thea integration (Sonarr/Radarr on same server)
    sonarr_url: str = "http://localhost:8989"
    sonarr_api_key: str = ""
    radarr_url: str = "http://localhost:7878"
    radarr_api_key: str = ""

    # Plex processing server (via Tailscale or local Docker container)
    plex_processing_url: str = "http://100.108.190.10:8006"

    # URL the processing server uses to push results back to this API
    # When both run in Docker: http://narralytica-backend:8005
    # When processing is remote: http://<tailscale-ip>:8005
    api_callback_url: str = "http://narralytica-backend:8005"

    model_config = {"env_file": ".env"}


settings = Settings()

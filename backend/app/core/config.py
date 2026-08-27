from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "sentinel-api"
    app_version: str = "1.0.0"
    sentinel_build_sha: str | None = Field(default=None, max_length=64)
    sentinel_build_time: str | None = Field(default=None, max_length=64)
    sentinel_env: str = "development"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    websocket_allowed_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    )
    telemetry_max_body_bytes: int = Field(default=262_144, ge=1, le=10_485_760)
    collector_api_key: str | None = Field(default=None, min_length=16, max_length=512)
    lab_telemetry_stale_seconds: int = Field(default=120, ge=30, le=3600)
    sentinel_simulator_enabled: bool = False
    sentinel_simulation_key: str = Field(
        default="sentinel_local_simulation_key_change_me", min_length=16, max_length=512
    )
    simulator_control_url: str = "http://sentinel-lab-gateway:8082"
    simulator_action_timeout_seconds: int = Field(default=40, ge=1, le=60)
    simulator_scenario_timeout_seconds: int = Field(default=180, ge=30, le=300)
    simulator_settle_seconds: int = Field(default=4, ge=0, le=10)
    sentinel_ai_enabled: bool = False
    sentinel_ai_provider: str = ""
    sentinel_ai_model: str = ""
    sentinel_ai_api_key: str | None = Field(default=None, max_length=2048)
    sentinel_ai_base_url: str = "https://api.openai.com/v1"
    sentinel_ai_timeout_seconds: int = Field(default=30, ge=1, le=120)
    sentinel_ai_max_context_events: int = Field(default=50, ge=5, le=250)
    sentinel_ai_max_network_relationships: int = Field(default=50, ge=1, le=100)
    sentinel_ai_question_history: int = Field(default=10, ge=0, le=20)
    database_url: str = Field(
        default="postgresql+asyncpg://sentinel:sentinel_dev_only_change_me@localhost:5432/sentinel"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_url.split(",") if origin.strip()]

    @property
    def websocket_origins(self) -> set[str]:
        return {
            origin.strip() for origin in self.websocket_allowed_origins.split(",") if origin.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()

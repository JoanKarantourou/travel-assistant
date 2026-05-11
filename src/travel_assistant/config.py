from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_", env_file=".env", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    name: str = "travel_assistant"
    user: str = "travel"
    password: str = "travel"

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ANTHROPIC_", env_file=".env", extra="ignore")

    api_key: str = ""
    model: str = "claude-sonnet-4-5"


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "travel-assistant"
    prometheus_port: int = 9090


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = "INFO"
    environment: str = "development"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    app: AppSettings = Field(default_factory=AppSettings)


@lru_cache
def get_settings() -> Settings:
    return Settings()

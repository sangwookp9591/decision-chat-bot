from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / ".env", env_file_encoding="utf-8", extra="ignore")

    jev_api_key: SecretStr = SecretStr("")
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    # Matches the docker-compose local default; production must set NEO4J_PASSWORD.
    neo4j_password: SecretStr = SecretStr("development-only")
    jev_mode: str = "live"
    data_dir: Path = Path(".data")
    neo4j_connection_timeout_seconds: float = 3.0
    neo4j_connection_acquisition_timeout_seconds: float = 5.0
    neo4j_transaction_retry_seconds: float = 3.0
    auth_db_timeout_seconds: float = 8.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

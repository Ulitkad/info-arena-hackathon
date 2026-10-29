from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    bot_token: str = ""
    admin_max_id: int = 0
    secret_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/arena.db"
    base_app_url: str = "http://localhost:5173"
    bot_username: str = ""
    bot_api_url: str = "https://platform-api2.max.ru"
    max_ca_bundle: str = ""
    upload_dir: Path = Path("uploads")
    dev_auth: bool = False
    seed_demo: bool = False

    @model_validator(mode="after")
    def validate_secret(self):
        if len(self.secret_key) < 32 or self.secret_key.startswith("replace-with"):
            raise ValueError("Set SECRET_KEY to a random secret of at least 32 characters")
        if self.seed_demo and not self.dev_auth:
            raise ValueError("SEED_DEMO requires DEV_AUTH=true")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

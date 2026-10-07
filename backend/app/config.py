from functools import lru_cache
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ExpenseGuard"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    DEFAULT_CURRENCY: str = "INR"
    APPROVAL_LIMIT: float = 10000.0

    # Firefly III Configuration
    FIREFLY_APP_KEY: str = "SomeRandomStringOf32Characters!!"
    FIREFLY_SITE_URL: str = "http://localhost:8080"
    FIREFLY_EXTERNAL_URL: str = "http://localhost:8080"
    FIREFLY_API_TOKEN: str = ""
    FIREFLY_WEBHOOK_SECRET: str = "expenseguard_webhook_secret_key_123"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./expenseguard.db"
    DATABASE_URL_SYNC: str = "sqlite:///./expenseguard.db"

    # Security & Auth
    SECRET_KEY: str = "expenseguard_super_secret_jwt_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ML & PyOD Configuration
    CONTAMINATION: float = 0.05
    MODELS_ENABLED: str = "ecod,iforest"
    MIN_TX_FOR_CATEGORY_MODEL: int = 30
    COLD_START_MIN_ROWS: int = 50
    MODELS_DIR: str = str(Path(__file__).resolve().parent.parent / "models_data")

    # Risk Combiner & Tiers
    COMBINER_WEIGHT_ECOD: float = 0.5
    COMBINER_WEIGHT_IFOREST: float = 0.5
    TIER_LOW_MAX: int = 39
    TIER_MEDIUM_MAX: int = 69

    # Alerting
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_FROM: str = "alerts@expenseguard.local"
    SLACK_WEBHOOK_URL: str = ""
    ALERT_HIGH_SEVERITY_ONLY: bool = True

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def enabled_models_list(self) -> List[str]:
        return [m.strip().lower() for m in self.MODELS_ENABLED.split(",") if m.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()

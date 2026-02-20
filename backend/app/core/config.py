import os
import json
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# ----------------------------
# Constants (NOT Pydantic fields)
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # .../app/core
APP_DIR = os.path.dirname(BASE_DIR)                    # .../app
AI_DIR = os.path.join(APP_DIR, "ai")                   # .../app/ai

ARTIFACTS_DIR = os.path.join(AI_DIR, "artifacts")
MODELS_DIR = os.path.join(ARTIFACTS_DIR, "models")
FORECASTS_DIR = os.path.join(ARTIFACTS_DIR, "forecasts")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(FORECASTS_DIR, exist_ok=True)

CHURN_MODEL_PATH = os.path.join(MODELS_DIR, "churn_logistic.joblib")
REVENUE_MODEL_PATH = os.path.join(MODELS_DIR, "revenue_prophet.pkl")
REVENUE_FORECAST_PATH = os.path.join(FORECASTS_DIR, "revenue_forecast_latest.json")


def parse_cors_list(raw: str) -> List[str]:
    """
    Handles:
      CORS_ALLOWED_ORIGINS=["http://localhost:5173"]
    stored as string in .env, and converts it to python list[str].
    """
    if not raw:
        return []

    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x) for x in data]
        except Exception:
            pass

    # fallback: comma-separated string
    if "," in raw:
        return [x.strip().strip('"').strip("'") for x in raw.split(",") if x.strip()]

    return [raw.strip('"').strip("'")]


class Settings(BaseSettings):
    # ✅ Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # ----------------------------
    # These match your .env exactly
    # ----------------------------
    APP_NAME: str = "SmartServeAI"
    ENV: str = "dev"

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ALLOWED_ORIGINS: str = '["http://localhost:5173"]'

    JWT_SECRET: str = "change_me"
    JWT_ACCESS_MINUTES: int = 30
    JWT_REFRESH_DAYS: int = 14

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # ----------------------------
    # Helper computed property
    # ----------------------------
    @property
    def cors_origins(self) -> List[str]:
        return parse_cors_list(self.CORS_ALLOWED_ORIGINS)


settings = Settings()
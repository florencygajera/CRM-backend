import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# ✅ constants should be outside Settings (NOT model fields)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # .../app/core
AI_DIR = os.path.join(os.path.dirname(BASE_DIR), "ai")  # .../app/ai

ARTIFACTS_DIR = os.path.join(AI_DIR, "artifacts")
MODELS_DIR = os.path.join(ARTIFACTS_DIR, "models")
FORECASTS_DIR = os.path.join(ARTIFACTS_DIR, "forecasts")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(FORECASTS_DIR, exist_ok=True)

CHURN_MODEL_PATH = os.path.join(MODELS_DIR, "churn_logistic.joblib")
REVENUE_MODEL_PATH = os.path.join(MODELS_DIR, "revenue_prophet.pkl")
REVENUE_FORECAST_PATH = os.path.join(FORECASTS_DIR, "revenue_forecast_latest.json")


class Settings(BaseSettings):
    # Pydantic v2 config
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Put only actual ENV-configurable fields here (examples)
    APP_NAME: str = "CRM Backend"
    ENV: str = "dev"


settings = Settings()
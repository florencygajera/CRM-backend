from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "SmartServeAI"
    ENV: str = "dev"
    DATABASE_URL: str

    JWT_SECRET: str
    JWT_ACCESS_MINUTES: int = 30
    JWT_REFRESH_DAYS: int = 14

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    
    CORS_ALLOWED_ORIGINS: List[str] = ["https://your-frontend.com"]

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
    MODELS_DIR = os.path.join(ARTIFACTS_DIR, "models")
    FORECASTS_DIR = os.path.join(ARTIFACTS_DIR, "forecasts")

    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(FORECASTS_DIR, exist_ok=True)

    CHURN_MODEL_PATH = os.path.join(MODELS_DIR, "churn_logistic.joblib")
    REVENUE_MODEL_PATH = os.path.join(MODELS_DIR, "revenue_prophet.pkl")
    REVENUE_FORECAST_PATH = os.path.join(FORECASTS_DIR, "revenue_forecast_latest.json")


settings = Settings()

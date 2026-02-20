import os
from app.core.config import CHURN_MODEL_PATH, REVENUE_MODEL_PATH, REVENUE_FORECAST_PATH
# Base: .../backend/app/ai_models
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
MODELS_DIR = os.path.join(ARTIFACTS_DIR, "models")
FORECASTS_DIR = os.path.join(ARTIFACTS_DIR, "forecasts")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(FORECASTS_DIR, exist_ok=True)

CHURN_MODEL_PATH = os.path.join(MODELS_DIR, "churn_logistic.joblib")
REVENUE_MODEL_PATH = os.path.join(MODELS_DIR, "revenue_prophet.pkl")
REVENUE_FORECAST_PATH = os.path.join(FORECASTS_DIR, "revenue_forecast_latest.json")
# Re-export AI model paths from core config
# This allows the ai_models modules to import from .config
from app.core.config import settings

CHURN_MODEL_PATH = settings.CHURN_MODEL_PATH
REVENUE_MODEL_PATH = settings.REVENUE_MODEL_PATH
REVENUE_FORECAST_PATH = settings.REVENUE_FORECAST_PATH

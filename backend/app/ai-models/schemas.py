from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class RevenueTrainRequest(BaseModel):
    csv_path: str = Field(..., description="Path to revenue_daily.csv with columns date,revenue")
    horizon_days: int = 30

class RevenueForecastResponse(BaseModel):
    horizon_days: int
    forecast: List[Dict[str, Any]]
    slow_days: List[Dict[str, Any]]

class ChurnTrainRequest(BaseModel):
    csv_path: str = Field(..., description="Path to churn_dataset.csv")
    threshold_high_risk: float = 0.7

class ChurnScoreResponse(BaseModel):
    churn_probability: float
    risk_level: str
    threshold_high_risk: float
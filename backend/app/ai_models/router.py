import os
from fastapi import APIRouter, HTTPException, Query, Depends

from app.core.deps import require_roles
from app.models.user import UserRole

from .schemas import (
    RevenueTrainRequest, RevenueForecastResponse,
    ChurnTrainRequest, ChurnScoreResponse,
)
from .ai_revenue_prophet import RevenueConfig, load_revenue_from_csv, train_and_save_revenue_model
from .ai_churn_logistic import ChurnConfig, load_churn_from_csv, train_churn_model, score_customer
from .storage import load_json
from .config import REVENUE_FORECAST_PATH

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


# ----------------------
# Revenue Forecasting
# ----------------------
@router.post("/revenue/train", response_model=RevenueForecastResponse, dependencies=[Depends(require_roles(UserRole.OWNER))])
def revenue_train(req: RevenueTrainRequest):
    try:
        if not os.path.exists(req.csv_path):
            raise FileNotFoundError(req.csv_path)

        df = load_revenue_from_csv(req.csv_path)
        cfg = RevenueConfig(horizon_days=req.horizon_days)

        payload = train_and_save_revenue_model(df, cfg)
        return payload
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/revenue/forecast/latest", response_model=RevenueForecastResponse, dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.MANAGER))])
def revenue_latest():
    try:
        payload = load_json(REVENUE_FORECAST_PATH)
        return payload
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"No forecast found. Train first. Error: {e}")


# ----------------------
# Churn Prediction
# ----------------------
@router.post("/churn/train", dependencies=[Depends(require_roles(UserRole.OWNER))])
def churn_train(req: ChurnTrainRequest):
    try:
        if not os.path.exists(req.csv_path):
            raise FileNotFoundError(req.csv_path)

        df = load_churn_from_csv(req.csv_path)
        cfg = ChurnConfig(threshold_high_risk=req.threshold_high_risk)
        result = train_churn_model(df, cfg)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/churn/score/{customer_id}", response_model=ChurnScoreResponse, dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.MANAGER))])
def churn_score_customer(
    customer_id: int,
    threshold: float = Query(0.7, ge=0.0, le=1.0),
):
    """
    Demo scoring: replace the 'features' dict with DB-calculated features.
    For now, it returns a score using placeholder values.
    """
    # TODO: Replace with DB aggregation from your CRM tables
    features = {
        "days_since_last_visit": 75,
        "total_visits": 6,
        "avg_spending": 900,
        "cancellation_frequency": 0.20,
    }

    try:
        return score_customer(features, threshold_high_risk=threshold)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/churn/high-risk", dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.MANAGER))])
def churn_high_risk(threshold: float = Query(0.7, ge=0.0, le=1.0)):
    """
    Demo endpoint: in real CRM, query all customers, compute features, score each, filter prob > threshold.
    """
    # TODO: Replace with DB loop
    demo_customers = [
        {"customer_id": 1, "days_since_last_visit": 120, "total_visits": 3, "avg_spending": 800, "cancellation_frequency": 0.33},
        {"customer_id": 2, "days_since_last_visit": 15, "total_visits": 18, "avg_spending": 1500, "cancellation_frequency": 0.04},
        {"customer_id": 3, "days_since_last_visit": 90, "total_visits": 4, "avg_spending": 880, "cancellation_frequency": 0.29},
    ]

    out = []
    for c in demo_customers:
        score = score_customer(
            {
                "days_since_last_visit": c["days_since_last_visit"],
                "total_visits": c["total_visits"],
                "avg_spending": c["avg_spending"],
                "cancellation_frequency": c["cancellation_frequency"],
            },
            threshold_high_risk=threshold,
        )
        if score["churn_probability"] > threshold:
            out.append({"customer_id": c["customer_id"], **score})

    return {"threshold": threshold, "high_risk_customers": out}

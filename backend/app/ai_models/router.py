"""AI model routes: revenue forecasting and churn prediction."""

import os

from fastapi import APIRouter, HTTPException, Query

from .schemas import (
    RevenueTrainRequest, RevenueForecastResponse,
    ChurnTrainRequest, ChurnScoreResponse,
)
from .ai_revenue_prophet import (
    RevenueConfig, load_revenue_from_csv, train_and_save_revenue_model,
)
from .ai_churn_logistic import (
    ChurnConfig, load_churn_from_csv, train_churn_model, score_customer,
)
from .storage import load_json
from .config import REVENUE_FORECAST_PATH

# Prefix is set by the parent aggregation router — no prefix here.
router = APIRouter()


# ── Revenue Forecasting ──────────────────────────────────────────────────
@router.post("/revenue/train", response_model=RevenueForecastResponse)
def revenue_train(req: RevenueTrainRequest):
    try:
        if not os.path.exists(req.csv_path):
            raise FileNotFoundError(req.csv_path)

        df = load_revenue_from_csv(req.csv_path)
        cfg = RevenueConfig(horizon_days=req.horizon_days)
        return train_and_save_revenue_model(df, cfg)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/revenue/forecast/latest", response_model=RevenueForecastResponse)
def revenue_latest():
    try:
        return load_json(REVENUE_FORECAST_PATH)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast found. Train first. Error: {exc}",
        )


# ── Churn Prediction ─────────────────────────────────────────────────────
@router.post("/churn/train")
def churn_train(req: ChurnTrainRequest):
    try:
        if not os.path.exists(req.csv_path):
            raise FileNotFoundError(req.csv_path)

        df = load_churn_from_csv(req.csv_path)
        cfg = ChurnConfig(threshold_high_risk=req.threshold_high_risk)
        return train_churn_model(df, cfg)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/churn/score/{customer_id}", response_model=ChurnScoreResponse)
def churn_score_customer(
    customer_id: int,
    threshold: float = Query(0.7, ge=0.0, le=1.0),
):
    """
    Demo scoring — replace the hard-coded *features* dict with
    DB-calculated values per customer in production.
    """
    # TODO: Replace with DB aggregation from CRM tables
    features = {
        "days_since_last_visit": 75,
        "total_visits": 6,
        "avg_spending": 900,
        "cancellation_frequency": 0.20,
    }
    try:
        return score_customer(features, threshold_high_risk=threshold)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/churn/high-risk")
def churn_high_risk(threshold: float = Query(0.7, ge=0.0, le=1.0)):
    """
    Demo endpoint — in a real CRM you would query all customers,
    compute features from their history, score each, and filter.
    """
    # TODO: Replace with DB loop
    demo_customers = [
        {"customer_id": 1, "days_since_last_visit": 120, "total_visits": 3,
         "avg_spending": 800, "cancellation_frequency": 0.33},
        {"customer_id": 2, "days_since_last_visit": 15, "total_visits": 18,
         "avg_spending": 1500, "cancellation_frequency": 0.04},
        {"customer_id": 3, "days_since_last_visit": 90, "total_visits": 4,
         "avg_spending": 880, "cancellation_frequency": 0.29},
    ]

    high_risk = []
    for c in demo_customers:
        result = score_customer(
            {
                "days_since_last_visit": c["days_since_last_visit"],
                "total_visits": c["total_visits"],
                "avg_spending": c["avg_spending"],
                "cancellation_frequency": c["cancellation_frequency"],
            },
            threshold_high_risk=threshold,
        )
        if result["churn_probability"] > threshold:
            high_risk.append({"customer_id": c["customer_id"], **result})

    return {"threshold": threshold, "high_risk_customers": high_risk}
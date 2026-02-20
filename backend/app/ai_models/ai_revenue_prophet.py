from dataclasses import dataclass
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd
from prophet import Prophet

from .storage import save_pickle, load_pickle, save_json
from .config import REVENUE_MODEL_PATH, REVENUE_FORECAST_PATH


@dataclass
class RevenueConfig:
    horizon_days: int = 30
    weekly_seasonality: bool = True
    yearly_seasonality: bool = True
    daily_seasonality: bool = False
    interval_width: float = 0.80
    changepoint_prior_scale: float = 0.05
    seasonality_prior_scale: float = 10.0


def load_revenue_from_csv(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "date" not in df.columns or "revenue" not in df.columns:
        raise ValueError(f"CSV must contain date,revenue columns. Found: {list(df.columns)}")

    df = df.rename(columns={"date": "ds", "revenue": "y"})
    df["ds"] = pd.to_datetime(df["ds"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df = df.dropna(subset=["ds", "y"]).sort_values("ds")
    df = df[df["y"] >= 0]
    return df


def fill_missing_days(df: pd.DataFrame) -> pd.DataFrame:
    all_days = pd.date_range(df["ds"].min(), df["ds"].max(), freq="D")
    out = df.set_index("ds").reindex(all_days).rename_axis("ds").reset_index()
    out["y"] = out["y"].fillna(0.0)
    return out


def train_prophet(df: pd.DataFrame, cfg: RevenueConfig) -> Prophet:
    model = Prophet(
        weekly_seasonality=cfg.weekly_seasonality,
        yearly_seasonality=cfg.yearly_seasonality,
        daily_seasonality=cfg.daily_seasonality,
        interval_width=cfg.interval_width,
        changepoint_prior_scale=cfg.changepoint_prior_scale,
        seasonality_prior_scale=cfg.seasonality_prior_scale,
    )
    model.fit(df[["ds", "y"]])
    return model


def forecast(model: Prophet, horizon_days: int) -> pd.DataFrame:
    future = model.make_future_dataframe(periods=horizon_days, freq="D")
    fc = model.predict(future)
    return fc[["ds", "yhat", "yhat_lower", "yhat_upper"]]


def identify_slow_days(forecast_df: pd.DataFrame, horizon_days: int, slow_quantile: float = 0.20) -> pd.DataFrame:
    future_only = forecast_df.tail(horizon_days).copy()
    threshold = float(future_only["yhat"].quantile(slow_quantile))
    future_only["is_slow_day"] = future_only["yhat"] <= threshold
    future_only["slow_threshold"] = threshold
    future_only["weekday"] = pd.to_datetime(future_only["ds"]).dt.day_name()
    return future_only


def promotion_suggestion(weekday: str) -> str:
    if weekday in ["Tuesday", "Wednesday"]:
        return "Mid-week offer (5–10% off / bundle deal)"
    if weekday == "Monday":
        return "Start-week boost (referral coupon / limited discount)"
    return "Targeted promo (combo pack / add-on service)"


def train_and_save_revenue_model(
    revenue_df: pd.DataFrame,
    cfg: RevenueConfig,
) -> Dict[str, Any]:
    revenue_df = fill_missing_days(revenue_df)
    model = train_prophet(revenue_df, cfg)

    save_pickle(REVENUE_MODEL_PATH, model)

    fc = forecast(model, cfg.horizon_days)
    slow = identify_slow_days(fc, cfg.horizon_days, slow_quantile=0.20)
    slow["promotion_suggestion"] = slow["weekday"].apply(lambda w: promotion_suggestion(str(w)))

    payload = {
        "horizon_days": cfg.horizon_days,
        "forecast": fc.to_dict(orient="records"),
        "slow_days": slow[slow["is_slow_day"]].to_dict(orient="records"),
    }

    save_json(REVENUE_FORECAST_PATH, payload)
    return payload


def load_revenue_model() -> Prophet:
    return load_pickle(REVENUE_MODEL_PATH)

from dataclasses import dataclass
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from joblib import dump, load

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, precision_recall_fscore_support

from .config import CHURN_MODEL_PATH


@dataclass
class ChurnConfig:
    test_size: float = 0.2
    random_state: int = 42
    threshold_high_risk: float = 0.7
    class_weight: str = "balanced"


def load_churn_from_csv(csv_path: str) -> pd.DataFrame:
    # Robust delimiter detection + BOM handling
    df = pd.read_csv(csv_path, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]

    required = ["days_since_last_visit", "total_visits", "avg_spending", "cancellation_frequency", "churn"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}. Detected: {list(df.columns)}")

    for c in required:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=required)
    df = df[df["days_since_last_visit"] >= 0]
    df = df[df["total_visits"] >= 0]
    df = df[df["avg_spending"] >= 0]
    df = df[(df["cancellation_frequency"] >= 0) & (df["cancellation_frequency"] <= 1)]
    df = df[df["churn"].isin([0, 1])]
    return df


def build_pipeline(cfg: ChurnConfig) -> Pipeline:
    model = LogisticRegression(class_weight=cfg.class_weight, max_iter=2000)
    return Pipeline([("scaler", StandardScaler()), ("model", model)])


def train_churn_model(df: pd.DataFrame, cfg: ChurnConfig) -> Dict[str, Any]:
    X = df[["days_since_last_visit", "total_visits", "avg_spending", "cancellation_frequency"]].copy()
    y = df["churn"].astype(int).copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=cfg.test_size,
        random_state=cfg.random_state,
        stratify=y if y.nunique() > 1 else None
    )

    pipe = build_pipeline(cfg)
    pipe.fit(X_train, y_train)

    probs = pipe.predict_proba(X_test)[:, 1]
    preds = (probs >= cfg.threshold_high_risk).astype(int)

    auc = roc_auc_score(y_test, probs) if y_test.nunique() > 1 else float("nan")
    pr, rc, f1, _ = precision_recall_fscore_support(y_test, preds, average="binary", zero_division=0)

    dump(pipe, CHURN_MODEL_PATH)

    return {
        "saved_model_path": CHURN_MODEL_PATH,
        "rows_used": int(len(df)),
        "roc_auc": float(auc),
        "precision": float(pr),
        "recall": float(rc),
        "f1": float(f1),
        "threshold_high_risk": float(cfg.threshold_high_risk),
        "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
        "report": classification_report(y_test, preds, zero_division=0),
    }


def load_churn_model() -> Pipeline:
    return load(CHURN_MODEL_PATH)


def score_customer(features: Dict[str, float], threshold_high_risk: float = 0.7) -> Dict[str, Any]:
    pipe = load_churn_model()

    X = pd.DataFrame([{
        "days_since_last_visit": float(features["days_since_last_visit"]),
        "total_visits": float(features["total_visits"]),
        "avg_spending": float(features["avg_spending"]),
        "cancellation_frequency": float(features["cancellation_frequency"]),
    }])

    prob = float(pipe.predict_proba(X)[0, 1])
    risk = "HIGH" if prob > threshold_high_risk else ("MEDIUM" if prob >= 0.4 else "LOW")
    return {"churn_probability": prob, "risk_level": risk, "threshold_high_risk": threshold_high_risk}

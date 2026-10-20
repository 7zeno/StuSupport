"""Loads the trained Random Forest and turns a student's latest record into a risk prediction."""
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from ..config import get_settings

settings = get_settings()

LABELS = {
    "cgpa": "CGPA",
    "sgpa": "SGPA (latest semester)",
    "attendance_pct": "Attendance",
    "backlogs": "Active backlogs",
    "fee_paid": "Fee payment",
}


class ModelNotTrained(RuntimeError):
    pass


@lru_cache
def _load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise ModelNotTrained(f"No model at {p}. Run: python ml/train.py --source synthetic")
    return joblib.load(p)


def reload_model() -> None:
    _load.cache_clear()


def model_info() -> dict | None:
    try:
        return _load(str(settings.model_path))["metrics"]
    except ModelNotTrained:
        return None


def risk_level(probability: float) -> str:
    if probability >= settings.high_threshold:
        return "High"
    if probability >= settings.medium_threshold:
        return "Medium"
    return "Low"


def _record_values(record) -> dict:
    return {
        "cgpa": float(record.cgpa),
        "sgpa": float(record.sgpa),
        "attendance_pct": float(record.attendance_pct),
        "backlogs": int(record.backlogs),
        "fee_paid": int(bool(record.fee_paid)),
    }


def explain(values: dict, features: list[str], importances: dict, reference: dict) -> list[dict]:
    """Human-readable factors, ordered by model importance, flagged against simple academic thresholds
    and the median of non-dropout students in the training data."""
    factors = []
    for f in sorted(values, key=lambda k: -importances.get(k, 0)):
        v = values[f]
        ref = reference.get(f)
        used = f in features
        if f == "attendance_pct":
            sev = "concern" if v < 65 else "watch" if v < 75 else "ok"
            detail = f"{v:.0f}% attendance" + (" — below the 75% requirement" if v < 75 else "")
        elif f == "backlogs":
            sev = "concern" if v >= 3 else "watch" if v >= 1 else "ok"
            detail = "No pending backlogs" if v == 0 else f"{v} pending backlog{'s' if v != 1 else ''}"
        elif f == "fee_paid":
            sev = "ok" if v else "concern"
            detail = "Fees are up to date" if v else "Fee payment is pending"
            v = bool(v)
        elif f in ("cgpa", "sgpa"):
            sev = "concern" if v < 5.5 else "watch" if v < 6.5 else "ok"
            detail = f"{LABELS[f]} {v:.2f}"
            if ref is not None:
                detail += f" (typical for students who continue: {ref:.2f})"
        else:
            continue
        if not used:
            detail += " — not used by the current model"
        factors.append({"feature": f, "label": LABELS[f], "value": v, "detail": detail, "severity": sev})
    return factors


def predict_record(record) -> dict:
    bundle = _load(str(settings.model_path))
    features: list[str] = bundle["features"]
    metrics: dict = bundle["metrics"]
    values = _record_values(record)
    X = pd.DataFrame([{f: values[f] for f in features}], columns=features, dtype=float)
    probability = float(bundle["pipeline"].predict_proba(X)[0, 1])
    return {
        "probability": round(probability, 4),
        "risk_level": risk_level(probability),
        "factors": explain(values, features, metrics.get("feature_importances", {}), metrics.get("reference", {})),
        "model_version": metrics["model_version"],
    }

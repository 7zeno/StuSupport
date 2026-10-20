"""Train and evaluate the Random Forest dropout model.

    # demo data (all five app features)
    python ml/train.py --source synthetic

    # Martins et al. (2021) dataset from UCI (id 697)
    python ml/train.py --source uci --csv ml/data/data.csv

Writes ml/artifacts/model.joblib (pipeline + metadata) and ml/artifacts/metrics.json.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline

from data_sources import load_synthetic, load_uci

HERE = Path(__file__).parent


# Direction each feature is allowed to push dropout risk (+1 raises, -1 lowers).
# Without this, sparse regions of the data (e.g. the very high grades that are rare in
# the UCI dataset) can produce nonsense such as a 9.2 CGPA scoring higher risk than 7.5.
MONOTONIC = {"cgpa": -1, "sgpa": -1, "attendance_pct": -1, "backlogs": 1, "fee_paid": -1}


def build_pipeline(seed: int, features: list[str]) -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            (
                "rf",
                RandomForestClassifier(
                    n_estimators=400,
                    min_samples_leaf=3,
                    class_weight="balanced",  # dropouts are the minority class
                    monotonic_cst=[MONOTONIC.get(f, 0) for f in features],
                    n_jobs=-1,
                    random_state=seed,
                ),
            ),
        ]
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["synthetic", "uci"], default="synthetic")
    ap.add_argument("--csv", type=Path, help="CSV path (defaults to ml/data/synthetic_students.csv)")
    ap.add_argument("--drop-enrolled", action="store_true", help="UCI only: drop still-enrolled students")
    ap.add_argument("--out-dir", type=Path, default=HERE / "artifacts")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if args.source == "synthetic":
        csv = args.csv or HERE / "data" / "synthetic_students.csv"
        if not csv.exists():
            from generate_synthetic import generate

            csv.parent.mkdir(parents=True, exist_ok=True)
            generate(4000, args.seed).to_csv(csv, index=False)
            print(f"Generated synthetic dataset at {csv}")
        df, features = load_synthetic(csv)
    else:
        if not args.csv:
            ap.error("--csv is required for --source uci")
        df, features = load_uci(args.csv, args.drop_enrolled)

    X, y = df[features].astype(float), df["dropout"].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=args.seed
    )

    pipe = build_pipeline(args.seed, features)
    cv = cross_validate(
        pipe,
        X_train,
        y_train,
        cv=StratifiedKFold(5, shuffle=True, random_state=args.seed),
        scoring=["accuracy", "precision", "recall", "f1", "roc_auc"],
    )
    pipe.fit(X_train, y_train)

    proba = pipe.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    rf = pipe.named_steps["rf"]
    importances = dict(sorted(zip(features, rf.feature_importances_.round(4).tolist()), key=lambda kv: -kv[1]))

    version = f"rf-{args.source}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    metrics = {
        "model_version": version,
        "source": args.source,
        "features": features,
        "drop_enrolled": bool(args.drop_enrolled),
        "n_rows": int(len(df)),
        "dropout_rate": round(float(y.mean()), 4),
        "test": {
            "accuracy": round(accuracy_score(y_test, pred), 4),
            "precision": round(precision_score(y_test, pred, zero_division=0), 4),
            "recall": round(recall_score(y_test, pred, zero_division=0), 4),
            "f1": round(f1_score(y_test, pred, zero_division=0), 4),
            "roc_auc": round(roc_auc_score(y_test, proba), 4),
            "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
        },
        "cv_5fold_mean": {k.removeprefix("test_"): round(float(np.mean(v)), 4) for k, v in cv.items() if k.startswith("test_")},
        "feature_importances": importances,
        # Reference distribution of non-dropouts, used to explain individual predictions.
        "reference": {f: round(float(X_train[y_train == 0][f].median()), 3) for f in features},
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipe, "features": features, "metrics": metrics}, args.out_dir / "model.joblib")
    (args.out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    print(f"Model {version} trained on {len(X_train)} rows with features {features}")
    for k, v in metrics["test"].items():
        if k != "confusion_matrix":
            print(f"  test {k:<9} {v:.3f}")
    print(f"  confusion matrix {metrics['test']['confusion_matrix']}")
    print(f"  importances {importances}")
    if args.source == "synthetic":
        print("NOTE: synthetic data - metrics are for pipeline testing only.")


if __name__ == "__main__":
    main()

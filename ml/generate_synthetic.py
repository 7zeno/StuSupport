"""Generate a synthetic student dataset with the five indicators the app tracks.

FOR DEVELOPMENT AND DEMOS ONLY. Relationships between features and dropout are
invented to be plausible; do not report metrics from this data as findings.

    python ml/generate_synthetic.py --n 4000 --out ml/data/synthetic_students.csv
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def generate(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ability = rng.normal(0, 1, n)          # academic preparedness
    engagement = rng.normal(0, 1, n)       # motivation / connection to campus
    fin_stress = rng.normal(0, 1, n)       # financial pressure
    engagement = 0.6 * engagement + 0.25 * ability - 0.15 * fin_stress

    cgpa = np.clip(6.9 + 1.1 * ability + 0.3 * engagement + rng.normal(0, 0.45, n), 2.0, 10.0)
    trend = 0.35 * engagement - 0.25 * fin_stress + rng.normal(0, 0.5, n)
    sgpa = np.clip(cgpa + trend, 0.0, 10.0)
    attendance = np.clip(80 + 9 * engagement - 2.5 * fin_stress + rng.normal(0, 6, n), 25, 100)
    backlogs = rng.poisson(np.exp(-0.4 - 1.1 * ability - 0.4 * engagement)).clip(0, 15)
    fee_paid = rng.random(n) < 1 / (1 + np.exp(-(1.8 - 1.4 * fin_stress)))

    logit = (
        -2.0
        - 0.75 * (cgpa - 6.9)
        - 0.45 * (sgpa - cgpa)
        - 0.07 * (attendance - 80)
        + 0.35 * backlogs
        + 1.1 * (~fee_paid)
        + 0.4 * fin_stress
        + rng.normal(0, 0.6, n)
    )
    dropout = rng.random(n) < 1 / (1 + np.exp(-logit))

    return pd.DataFrame(
        {
            "cgpa": cgpa.round(2),
            "sgpa": sgpa.round(2),
            "attendance_pct": attendance.round(1),
            "backlogs": backlogs.astype(int),
            "fee_paid": fee_paid.astype(int),
            "dropout": dropout.astype(int),
        }
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "data" / "synthetic_students.csv")
    args = ap.parse_args()
    df = generate(args.n, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows to {args.out} (dropout rate {df.dropout.mean():.1%})")

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Tuple

import sqlite3
import pandas as pd
import numpy as np

from config import DB_PATH, ALLOWED_EXERCISES

# ___Configuration___
SCENARIOS: Dict[str, float] = {
    "100%": 1.00,
    "75%": 0.75,
    "50%": 0.50,
}

BASELINE_GAINS: Dict[str, float] = {
    "Bench Press": 1.0,
    "Squat": 1.5,
    "Deadlift": 2.0
}

WEEKS_AHEAD = 12
K = 6
N_SIMS = 2000
SEED = 42


def estimate_sigma_from_diffs(weekly: pd.DataFrame) -> pd.Series:
    """
    Robust volatility estimate per lift based on WoW changes in weekly e1RM.
    Uses ALL data (high & low weeks) to avoid artificially inflating sigma
    when deload weeks are filtered out.
    """
    wk = weekly.copy()
    wk["week_start"] = pd.to_datetime(wk["week_start"], errors="raise")
    wk = wk.sort_values(["exercise", "week_start"])

    def robust_std(series: pd.Series) -> float:
        s = series.diff().dropna()
        if len(s) < 3:
            return 0.5  # safe default with very little data

        lo, hi = s.quantile([0.2, 0.8])
        # Remove extreme negative drops (deloads) and clip outliers
        s_clean = s[(s > -10) & (s >= lo) & (s <= hi)]
        s_clean = s_clean.clip(lower=-5, upper=5)

        if len(s_clean) >= 2:
            std = float(s_clean.std(ddof=1))
        else:
            std = float(s.std(ddof=1))

        return max(std, 0.25)

    # GroupBy apply directly on the series avoids index alignment warnings in pandas 2.x
    sigma = wk.groupby("exercise")["e1rm"].apply(robust_std)

    sigma_floor = {
        "Bench Press": 1.2,
        "Squat": 2.0,
        "Deadlift": 2.5
    }

    for lift, floor in sigma_floor.items():
        current_val = sigma.get(lift, np.nan)
        if pd.isna(current_val):
            sigma[lift] = floor
        else:
            sigma[lift] = max(current_val, floor)

    return sigma


def simulate_paths(
    e0: float,
    delta0: float,
    weeks_ahead: int,
    adherence_mult: float,
    sigma: float,
    k: int,
    n_sims: int,
    seed: int
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(weeks_ahead)

    # Diminishing returns with adherence multiplier
    expected_gain = (delta0 / np.log1p(t + k / 2)) * adherence_mult
    expected_gain = np.minimum(expected_gain, delta0)

    noise = rng.normal(loc=0, scale=sigma, size=(n_sims, weeks_ahead))
    increments = expected_gain + noise

    # Cumulative sum starting from e0
    paths = np.cumsum(increments, axis=1) + e0
    # Enforce a hard floor at 85% of starting e1RM
    paths = np.maximum(paths, e0 * 0.85)

    return paths


def choose_anchor_e1rm(exercise_history: pd.DataFrame, lookback: int = 3) -> float:
    hist = exercise_history.sort_values("week_start").tail(lookback)
    if hist.empty:
        return 0.0  # Fallback; should be caught earlier in main()
    return float(hist["e1rm"].max())


def classify_week_type(weekly: pd.DataFrame) -> pd.DataFrame:
    """Vectorized week classification. Replaces slow groupby.apply."""
    out = weekly.copy()
    medians = out.groupby("exercise")["e1rm"].median()
    thresholds = out["exercise"].map(lambda ex: medians[ex] * 0.85)
    out["week_type"] = np.where(out["e1rm"] < thresholds, "low", "high")
    return out


def main() -> None:
    print("build_forecasts.py started. Reading weekly_e1rm and writing forecast bands...")
    generated_at = datetime.now(timezone.utc).date().isoformat()

    conn = sqlite3.connect(str(DB_PATH))
    try:
        weekly = pd.read_sql_query(
            "SELECT * FROM weekly_e1rm ORDER BY week_start, exercise", conn
        )
        if weekly.empty:
            raise ValueError(
                "weekly_e1rm is empty. Run compute_weekly_e1rm.py first.")

        weekly = weekly[weekly["exercise"].isin(ALLOWED_EXERCISES)].copy()
        weekly["week_start"] = pd.to_datetime(
            weekly["week_start"], errors="raise")

        weekly = classify_week_type(weekly)
        weekly_high = weekly[weekly["week_type"] == "high"].copy()

        print("\nWeekly data with week_type")
        print(weekly[["week_start", "exercise", "e1rm",
              "week_type"]].to_string(index=False))

        last_week = weekly["week_start"].max()
        # Note: freq="W-MON" triggers a warning in pandas 2.2+. Use freq="W" or pd.offsets.Week(weekday=0) if strict.
        forecast_weeks = pd.date_range(
            start=last_week + pd.Timedelta(weeks=1), periods=WEEKS_AHEAD, freq="W-MON"
        )

        anchor_by_lift: Dict[str, float] = {}
        for exercise, group in weekly_high.groupby("exercise"):
            anchor_by_lift[exercise] = choose_anchor_e1rm(group, lookback=3)

        # FIX: Compute sigma on ALL weekly data, not just "high" weeks.
        # Filtering out deloads before diffing artificially inflates WoW deltas.
        sigma_by_lift = estimate_sigma_from_diffs(weekly)

        rows_out: List[Tuple[str, str, str, float,
                             float, float, float, float]] = []
        vintage_rows: List[Tuple[str, str, str, str,
                                 float, float, float, float, float]] = []

        for exercise in sorted(ALLOWED_EXERCISES):
            if exercise not in anchor_by_lift:
                print(
                    f"Skipping {exercise}: no 'high' week data to anchor forecast.")
                continue

            e0 = float(anchor_by_lift[exercise])
            print(f"{exercise}: anchor e0 = {e0:.2f}")

            delta0 = float(BASELINE_GAINS.get(exercise, 0.5))
            sigma = float(sigma_by_lift.get(exercise, 1.0))

            for scenario, mult in SCENARIOS.items():
                paths = simulate_paths(
                    e0=e0, delta0=delta0, weeks_ahead=WEEKS_AHEAD,
                    adherence_mult=mult, sigma=sigma, k=K, n_sims=N_SIMS, seed=SEED
                )

                p5, p10, p50, p90, p95 = np.percentile(
                    paths, [5, 10, 50, 90, 95], axis=0)

                for i, wk in enumerate(forecast_weeks):
                    row = (
                        wk.date().isoformat(), exercise, scenario,
                        float(p5[i]), float(p10[i]), float(
                            p50[i]), float(p90[i]), float(p95[i])
                    )
                    rows_out.append(row)
                    vintage_rows.append((generated_at, *row))

        with conn:
            conn.execute("DROP TABLE IF EXISTS forecast_bands;")
            conn.execute("""
                CREATE TABLE forecast_bands (
                    week_start TEXT NOT NULL, exercise TEXT NOT NULL, scenario TEXT NOT NULL,
                    p5 REAL NOT NULL, p10 REAL NOT NULL, p50 REAL NOT NULL, p90 REAL NOT NULL, p95 REAL NOT NULL,
                    PRIMARY KEY (week_start, exercise, scenario)
                );
            """)
            conn.executemany("""
                INSERT INTO forecast_bands (week_start, exercise, scenario, p5, p10, p50, p90, p95)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, rows_out)

            n = conn.execute(
                "SELECT COUNT(*) FROM forecast_bands;").fetchone()[0]
            print(f"✅ Saved forecast_bands rows: {n}")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS forecast_vintages(
                    generated_at TEXT NOT NULL, forecast_week TEXT NOT NULL, exercise TEXT NOT NULL,
                    scenario TEXT NOT NULL, p5 REAL NOT NULL, p10 REAL NOT NULL, p50 REAL NOT NULL,
                    p90 REAL NOT NULL, p95 REAL NOT NULL,
                    PRIMARY KEY (generated_at, forecast_week, exercise, scenario)
                );
            """)
            conn.executemany("""
                INSERT OR REPLACE INTO forecast_vintages
                (generated_at, forecast_week, exercise, scenario, p5, p10, p50, p90, p95)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, vintage_rows)

            n_vintages = conn.execute(
                "SELECT COUNT(*) FROM forecast_vintages;").fetchone()[0]
            print(f"✅ Saved rows in forecast_vintages: {n_vintages}")

    except Exception as e:
        print(f"❌ Forecast build failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()

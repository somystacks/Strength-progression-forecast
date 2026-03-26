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
}  # Dictionary of scenario names and adherence multipliers

# A simple starting point for "gain potential" per lift
# We'll refine this later with calibration (Phase 8-ish)
BASELINE_GAINS: Dict[str, float] = {
    "Bench Press": 0.5,  # as the smallest muscle groups it is more technical and sensitive to fatigue thus the slowest gain potential
    "Squat": 0.75,  # as the largest muscle groups it is more prone to neurological gains early thus the moderate gain potential
    "Deadlift": 1.0  # as it requires the biggest muscle recruitment it is predicted to be the most resilient thus the highest gain potential
}

WEEKS_AHEAD = 12  # Number of weeks to forecast ahead
K = 6  # Diminishing returns parameter
N_SIMS = 2000  # Number of simulation paths to generate
SEED = 42  # Random seed for reproducibility


def estimate_sigma_from_diffs(weekly: pd.DataFrame) -> pd.Series:
    """
    Robust volatility estimate per lift based on WoW changes in weekly e1RM.

    With few weeks of data, a deload week creates a huge negative diff
    that inflates std and makes forecast bands explode.
    """
    wk = weekly.copy()
    wk["week_start"] = pd.to_datetime(wk["week_start"], errors="raise")
    wk = wk.sort_values(["exercise", "week_start"])

    diffs = wk.groupby("exercise")["e1rm"].pct_change()

    def robust_std(s: pd.Series) -> float:
        s = s.dropna()

        if len(s) < 3:
            return 0.5  # safe default with very little data

        # Trim extreme values (handles deload weeks)
        lo = s.quantile(0.10)
        hi = s.quantile(0.90)

        s_trim = s[(s >= lo) & (s <= hi)]

        if len(s_trim) >= 2:
            std = float(s_trim.std(ddof=1))
        else:
            std = float(s.std(ddof=1))

        return max(std, 0.25)

    sigma = diffs.groupby(wk["exercise"]).apply(robust_std)

    sigma_floor = {
        "Bench Press": 1.2,
        "Squat": 2.0,
        "Deadlift": 2.5
    }

    for lift, floor in sigma_floor.items():
        current_val = sigma.get(lift, floor)
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
    """
    Diminishing returns model (increment form):
    expected_weekly_gain(t) = (delta0 / log1p(t + k)) * adherence_mult

    Then add Gaussian noise each week, and cum-sum to get the projected e1RM.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(weeks_ahead)

    # Calculate the expected weekly gains with diminishing returns and adherence multiplier
    expected_gain = (delta0 / np.log1p(t + k)) * adherence_mult
    # Cap the expected gain to the initial gain
    expected_gain = np.minimum(expected_gain, delta0)

    # Generate random noise for each simulation path and week based on the specified sigma
    noise = rng.normal(loc=0, scale=sigma, size=(n_sims, weeks_ahead))

    # Calculate the weekly increments by adding the expected gain and random noise
    increments = expected_gain + noise

    # Calculate the cumulative sum of increments to get the projected e1RM for each week,
    # starting from the initial e1RM (e0).
    # Note: paths[:, 0] represents e1RM after week 1, not the starting point.
    paths = np.cumsum(increments, axis=1) + e0

    # Cap the projected e1RM at 85% of the initial e1RM (floor)
    paths = np.maximum(paths, e0 * 0.85)

    return paths


def main() -> None:
    print("Build_forecasts.py started, Reading weekly_e1rm and writing forecast bands...")
    generated_at = datetime.now(timezone.utc).date().isoformat()

    conn = sqlite3.connect(str(DB_PATH))

    try:
        weekly = pd.read_sql_query(
            "SELECT * FROM weekly_e1rm ORDER BY week_start, exercise", conn
        )

        if weekly.empty:
            raise ValueError(
                "weekly_e1rm is empty. Run compute_weekly_e1rm.py first.")

        # Keep only modeled lifts
        weekly = weekly[weekly["exercise"].isin(ALLOWED_EXERCISES)].copy()
        # Convert week_start column to datetime
        weekly["week_start"] = pd.to_datetime(
            weekly["week_start"], errors="raise")

        # Determine the forecast grid: weekly Mondays from the latest observed week_start
        last_week = weekly["week_start"].max()
        # Generate a range of forecast weeks starting from the last observed week
        forecast_weeks = pd.date_range(
            start=last_week + pd.Timedelta(weeks=1), periods=WEEKS_AHEAD, freq="W-MON")

        # Latest observed e0 per lift
        latest = (
            weekly.sort_values("week_start")
            .groupby("exercise", as_index=False)
            .tail(1)
            .set_index("exercise")
        )

        sigma_by_lift = estimate_sigma_from_diffs(weekly)

        rows_out: List[Tuple[str, str, str, float,
                             float, float, float, float]] = []
        vintage_rows: List[Tuple[str, str, str, str,
                                 float, float, float, float, float]] = []

        for exercise in sorted(ALLOWED_EXERCISES):
            if exercise not in latest.index:
                print(f"Skipping {exercise}, no weekly data yet.")
                continue

            # Get the latest observed e1RM for the exercise
            e0 = float(latest.loc[exercise, "e1rm"])
            # Default to 0.5 if exercise is not in BASELINE_GAINS
            delta0 = float(BASELINE_GAINS.get(exercise, 0.5))
            # Default to 1.0 if exercise is not in sigma_by_lift
            sigma = float(sigma_by_lift.get(exercise, 1.0))

            for scenario, mult in SCENARIOS.items():
                paths = simulate_paths(
                    e0=e0,
                    delta0=delta0,
                    weeks_ahead=WEEKS_AHEAD,
                    adherence_mult=mult,
                    sigma=sigma,
                    k=K,
                    n_sims=N_SIMS,
                    seed=SEED,
                )

                p5, p10, p50, p90, p95 = np.percentile(
                    paths, [5, 10, 50, 90, 95], axis=0)

                for i, wk in enumerate(forecast_weeks):
                    rows_out.append(
                        (
                            wk.date().isoformat(),
                            exercise,
                            scenario,
                            float(p5[i]),
                            float(p10[i]),
                            float(p50[i]),
                            float(p90[i]),
                            float(p95[i]),
                        )
                    )

                    vintage_rows.append(
                        (
                            generated_at,
                            wk.date().isoformat(),
                            exercise,
                            scenario,
                            float(p5[i]),
                            float(p10[i]),
                            float(p50[i]),
                            float(p90[i]),
                            float(p95[i]),
                        )
                    )

        with conn:
            # Because forecast_bands is derived, we rebuild it cleanly each run.
            conn.execute("DROP TABLE IF EXISTS forecast_bands;")

            conn.execute("""
                CREATE TABLE forecast_bands (
                    week_start TEXT NOT NULL,
                    exercise TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    p5 REAL NOT NULL,
                    p10 REAL NOT NULL,
                    p50 REAL NOT NULL,
                    p90 REAL NOT NULL,
                    p95 REAL NOT NULL,
                    PRIMARY KEY (week_start, exercise, scenario)
                );
            """)

            conn.executemany("""
                INSERT INTO forecast_bands
                (week_start, exercise, scenario, p5, p10, p50, p90, p95)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, rows_out)

            n = conn.execute(
                "SELECT COUNT(*) FROM forecast_bands;").fetchone()[0]
            print(f"✅ Saved forecast_bands rows: {n}")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS forecast_vintages(
                    generated_at TEXT NOT NULL,
                    forecast_week TEXT NOT NULL,
                    exercise TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    p5 REAL NOT NULL,
                    p10 REAL NOT NULL,
                    p50 REAL NOT NULL,
                    p90 REAL NOT NULL,
                    p95 REAL NOT NULL,
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
            print(f"Saved rows in forecast_vintages: {n_vintages}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

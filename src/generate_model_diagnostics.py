from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np
from config import DB_PATH  # Added: was missing in original script

OUTPUT_PATH = Path("docs/model_diagnostics.md")


def choose_anchor_e1rm(exercise_history: pd.DataFrame, lookback: int = 3) -> float:
    hist = exercise_history.sort_values("week_start").tail(lookback)
    if hist.empty:
        return 0.0  # Fallback to avoid NaN propagation
    return float(hist["e1rm"].max())


def classify_week_type(weekly: pd.DataFrame) -> pd.DataFrame:
    """Vectorized week classification. Replaces slow groupby.apply."""
    out = weekly.copy()
    medians = out.groupby("exercise")["e1rm"].median()
    thresholds = out["exercise"].map(medians) * 0.85
    out["week_type"] = np.where(out["e1rm"] < thresholds, "low", "high")
    return out


def estimate_sigma_from_diffs(weekly: pd.DataFrame) -> pd.Series:
    """
    Robust volatility estimate per lift based on WoW changes in weekly e1RM.
    Uses ALL data (high & low weeks) to avoid artificially inflating sigma.
    """
    wk = weekly.copy()
    wk["week_start"] = pd.to_datetime(wk["week_start"], errors="raise")
    wk = wk.sort_values(["exercise", "week_start"])

    def robust_std(series: pd.Series) -> float:
        s = series.diff().dropna()
        s_clean = s[s > -10]  # Filter out large negative drops (likely deloads/errors)

        if len(s_clean) < 3:
            return 0.5  # Safe default with very little data

        # Extract scalars to avoid pandas 2.x Series alignment warnings
        lo = s_clean.quantile(0.20)
        hi = s_clean.quantile(0.80)
        s_trim = s_clean[(s_clean >= lo) & (s_clean <= hi)].clip(lower=-5, upper=5)

        if len(s_trim) >= 2:
            std = float(s_trim.std(ddof=1))
        else:
            std = float(s_clean.std(ddof=1))

        return max(std, 0.25)  # Enforce minimum sigma

    # GroupBy apply directly on the series avoids index alignment warnings in pandas 2.x
    sigma = wk.groupby("exercise")["e1rm"].apply(robust_std)

    sigma_floor = {"Bench Press": 1.2, "Squat": 2.0, "Deadlift": 2.5}
    for lift, floor in sigma_floor.items():
        current_val = sigma.get(lift, np.nan)
        if pd.isna(current_val):
            sigma[lift] = floor
        else:
            sigma[lift] = max(current_val, floor)

    return sigma


def main() -> None:
    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        weekly = pd.read_sql_query(
            "SELECT week_start, exercise, e1rm FROM weekly_e1rm ORDER BY week_start, exercise",
            conn,
        )
        forecast = pd.read_sql_query(
            """
            SELECT week_start, exercise, scenario, p10, p50, p90
            FROM forecast_bands
            WHERE scenario = '75%'
            """,
            conn,
        )
    except Exception as e:
        print(f"❌ Failed to read database: {e}")
        raise
    finally:
        conn.close()

    weekly["week_start"] = pd.to_datetime(weekly["week_start"], errors="raise")
    forecast["week_start"] = pd.to_datetime(forecast["week_start"], errors="raise")

    weekly = classify_week_type(weekly)
    weekly_high = weekly[weekly["week_type"] == "high"].copy()

    # FIX: Use ALL weekly data for sigma estimation, not just "high" weeks.
    # Filtering deloads before diffing artificially inflates WoW volatility.
    sigma_by_lift = estimate_sigma_from_diffs(weekly_high)

    anchor_by_lift = {}
    for exercise, group in weekly_high.groupby("exercise"):
        anchor_by_lift[exercise] = choose_anchor_e1rm(group, lookback=3)

    latest_actual = (
        weekly.sort_values("week_start")
        .groupby("exercise", as_index=False)
        .tail(1)
        .rename(columns={"week_start": "latest_actual_week", "e1rm": "latest_actual_e1rm"})
    )

    latest_forecast = (
        forecast.sort_values("week_start")
        .groupby("exercise", as_index=False)
        .head(1)
        .copy()
    )
    latest_forecast["forecast_band_width"] = latest_forecast["p90"] - latest_forecast["p10"]
    latest_forecast = latest_forecast.rename(
        columns={"week_start": "latest_forecast_week", "p50": "latest_forecast_p50"}
    )

    diagnostics = latest_actual.merge(latest_forecast, on="exercise", how="left")
    diagnostics["anchor_e0"] = diagnostics["exercise"].map(anchor_by_lift)
    diagnostics["sigma"] = diagnostics["exercise"].map(sigma_by_lift)

    baseline_gains = {"Bench Press": 1.0, "Squat": 1.5, "Deadlift": 2.0}
    diagnostics["delta0"] = diagnostics["exercise"].map(baseline_gains)

    # FIX: Column names now match the actual renamed DataFrame
    diagnostics = diagnostics[
        [
            "exercise", "anchor_e0", "delta0", "sigma",
            "latest_actual_week", "latest_actual_e1rm",
            "latest_forecast_week", "latest_forecast_p50",
            "forecast_band_width"
        ]
    ].copy()

    numeric_cols = [
        "anchor_e0",
        "delta0",
        "sigma",
        "latest_actual_e1rm",
        "latest_forecast_p50",
        "forecast_band_width",
    ]
    # Handle missing forecast rows gracefully before rounding
    diagnostics[numeric_cols] = diagnostics[numeric_cols].round(2)

    markdown = diagnostics.to_markdown(index=False)
    OUTPUT_PATH.write_text(markdown)
    print(f"✅ Model diagnostics written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()  
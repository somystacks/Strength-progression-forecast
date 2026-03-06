from __future__ import annotations
from config import DB_PATH
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for saving files


PLOTS_DIR = Path("docs/assets/plots")
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def load_data(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    weekly = pd.read_sql_query(
        "SELECT week_start, exercise, e1rm FROM weekly_e1rm ORDER BY week_start, exercise;",
        conn
    )
    bands = pd.read_sql_query(
        """
        SELECT week_start, exercise, scenario, p10, p50, p90
        FROM forecast_bands
        ORDER BY week_start, exercise, scenario;
        """,
        conn
    )

    # Ensure dates are datetime objects
    weekly["week_start"] = pd.to_datetime(weekly["week_start"])
    bands["week_start"] = pd.to_datetime(bands["week_start"])

    return weekly, bands


def plot_lift(
    weekly: pd.DataFrame,
    bands: pd.DataFrame,
    exercise: str,
    scenario: str = "75%"
) -> None:
    # Filter data
    w = weekly[weekly["exercise"] == exercise].sort_values("week_start").copy()
    b = bands[(bands["exercise"] == exercise) & (
        bands["scenario"] == scenario)].sort_values("week_start").copy()

    if w.empty:
        print(f"Skipping {exercise}: No weekly data")
        return

    if b.empty:
        print(f"Skipping {exercise}: No forecast data for scenario={scenario}")
        return

    forecast_start = b["week_start"].min()

    # Calculate Y limits with safety for NaNs
    y_min = min(w["e1rm"].min(), b["p10"].min()) - 5
    y_max = max(w["e1rm"].max(), b["p90"].max()) + 5

    plt.figure(figsize=(12, 6))

    # Uncertainty band
    plt.fill_between(
        b["week_start"],
        b["p10"],
        b["p90"],
        alpha=0.2,
        label=f"Forecast {scenario} 10-90% band"
    )

    # Forecast median
    plt.plot(
        b["week_start"],
        b["p50"],
        color="tab:blue",
        linewidth=2.2,
        label=f"Forecast p50 ({scenario})"
    )

    # Actual line
    plt.plot(
        w["week_start"],
        w["e1rm"],
        marker="o",
        linewidth=2.2,
        color="tab:orange",
        label="Actual weekly e1rm"
    )

    # Forecast start marker
    plt.axvline(forecast_start, linestyle="--", alpha=0.5,
                color="k", label="Forecast start")

    latest_actual = w.iloc[-1]["e1rm"]
    latest_date = w.iloc[-1]["week_start"]

    plt.annotate(
        f"Latest actual: {latest_actual:.1f} kg",
        xy=(latest_date, latest_actual),
        xytext=(10, 10),
        textcoords="offset points",
        fontsize=12,
        bbox={"boxstyle": "round, pad=0.3", "alpha": 0.2}
    )

    plt.title(f"{exercise} - Actual vs Forecast({scenario})", pad=10)

    # FIXED: Typos here (xlable -> xlabel, ylable -> ylabel)
    plt.xlabel("Week")
    plt.ylabel("e1RM (kg)")

    plt.ylim(y_min, y_max)

    ax = plt.gca()  # get current axis

    # FIXED: Use set_major_locator for Locator and set_major_formatter for Formatter
    ax.xaxis.set_major_locator(
        mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d - %b"))

    plt.grid(True, alpha=0.2)
    plt.legend(frameon=True)
    plt.tight_layout()

    output_path = PLOTS_DIR / \
        f"{exercise.lower().replace(' ', '_')}_forecast.png"

    try:
        plt.savefig(output_path, dpi=300)
        print(f"Saved plot: {output_path}")
    except Exception as e:
        print(f"Error saving plot for {exercise}: {e}")
    finally:
        plt.close()


def main() -> None:
    print("generate_forecast_plots.py started. Reading SQLite DB and generating forecast plots...")

    conn = sqlite3.connect(str(DB_PATH))
    try:
        weekly, bands = load_data(conn)

        # Verify these names match your database exactly (case-sensitive)
        lifts = ["Bench Press", "Squat", "Deadlift"]

        for lift in lifts:
            plot_lift(weekly, bands, lift, scenario="75%")

        print("✅ Forecast plots generated.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

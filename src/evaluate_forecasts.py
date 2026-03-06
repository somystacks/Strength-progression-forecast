from __future__ import annotations

import sqlite3
import pandas as pd

from config import DB_PATH


def main() -> None:
    print("evaluate_forecasts.py started. Computing forecast accuracy...")

    conn = sqlite3.connect(str(DB_PATH))

    try:
        weekly = pd.read_sql_query(
            "SELECT week_start, exercise, e1rm FROM weekly_e1rm",
            conn,
        )

        bands = pd.read_sql_query(
            """
            SELECT week_start, exercise, scenario, p10, p50, p90
            FROM forecast_bands
            WHERE scenario = '75%'
            """,
            conn,
        )

        weekly["week_start"] = pd.to_datetime(weekly["week_start"])
        bands["week_start"] = pd.to_datetime(bands["week_start"])

        df = weekly.merge(
            bands,
            on=["week_start", "exercise"],
            how="inner",
        )

        # New Guard
        if df.empty:
            print("No overlapping actual and forecast data yet. Evaluation deferred.")
            return

        # Avoid division by zero
        df = df[df["e1rm"] != 0].copy()

        df["error"] = df["e1rm"] - df["p50"]
        df["abs_error"] = df["error"].abs()
        df["error_pct"] = (df["abs_error"] / df["e1rm"]) * 100

        results = []

        for exercise, group in df.groupby("exercise"):
            mae = group["abs_error"].mean()
            mape = group["error_pct"].mean()
            bias = group["error"].mean()

            coverage = (
                (group["e1rm"] >= group["p10"]) &
                (group["e1rm"] <= group["p90"])
            ).mean()

            results.append(
                (
                    exercise,
                    float(mae),
                    float(mape),
                    float(bias),
                    float(coverage),
                    len(group),
                )
            )

        eval_df = pd.DataFrame(
            results,
            columns=[
                "exercise",
                "mae",
                "mape",
                "bias",
                "coverage",
                "n_observations",
            ],
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS forecast_evaluation (
                exercise TEXT,
                mae REAL,
                mape REAL,
                bias REAL,
                coverage REAL,
                n_observations INTEGER
            )
            """
        )

        conn.execute("DELETE FROM forecast_evaluation")

        eval_df.to_sql(
            "forecast_evaluation",
            conn,
            if_exists="append",
            index=False,
        )

    finally:
        conn.close()

    print(eval_df)
    print("Forecast evaluation saved.")


if __name__ == "__main__":
    main()

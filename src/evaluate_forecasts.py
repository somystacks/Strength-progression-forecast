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

        vintages = pd.read_sql_query(
            """
            SELECT
                generated_at,
                forecast_week,
                exercise,
                scenario,
                p10,
                p50,
                p90
            FROM forecast_vintages
            WHERE scenario = '75%'
            """,
            conn,
        )

        weekly["week_start"] = pd.to_datetime(weekly["week_start"])
        vintages["generated_at"] = pd.to_datetime(vintages["generated_at"])
        vintages["forecast_week"] = pd.to_datetime(vintages["forecast_week"])

        df = weekly.merge(
            vintages,
            left_on=["week_start", "exercise"],
            right_on=["forecast_week", "exercise"],
            how="inner",
        )

        # Keep only forecasts that existed before the forecasted week occured
        df = df[df["generated_at"] < df["forecast_week"]].copy()

        # For each actual week, keep the latest available forecast vintage made
        df = (
            df.sort_values(["exercise", "forecast_week", "generated_at"])
            .groupby(["exercise", "forecast_week"], as_index=False)
            .tail(1)
        )

        print("\nMatched evalutation rows:")
        print(
            df[[
                "exercise",
                "generated_at",
                "forecast_week",
                "e1rm",
                "p10",
                "p50",
                "p90",
            ]].sort_values(["exercise", "forecast_week"]).to_string(index=False)
        )

        # New Guard
        if df.empty:
            print("No overlapping actual and forecast vintages yet. Evaluation deferred.")
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

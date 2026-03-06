from __future__ import annotations

import sqlite3
import pandas as pd

from config import DB_PATH


def main() -> None:

    print("build_alerts.py started. Evaluating forecast vs actual performance...")

    conn = sqlite3.connect(str(DB_PATH))

    weekly = pd.read_sql_query(
        "SELECT week_start, exercise, e1rm FROM weekly_e1rm",
        conn,
    )

    bands = pd.read_sql_query(
        """
        SELECT week_start, exercise, p10, p90
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
        how="left",
    )

    df = df.sort_values(["exercise", "week_start"])

    alerts = []

    for exercise, group in df.groupby("exercise"):

        below_count = 0
        above_count = 0

        for _, row in group.iterrows():

            status = None

            if pd.isna(row["p10"]):
                continue

            if row["e1rm"] < row["p10"]:
                below_count += 1
                above_count = 0
            elif row["e1rm"] > row["p90"]:
                above_count += 1
                below_count = 0
            else:
                below_count = 0
                above_count = 0

            if below_count == 2:
                status = "YELLOW"
            elif below_count >= 3:
                status = "RED"
            elif above_count >= 3:
                status = "BLUE"

            if status:

                alerts.append(
                    (
                        row["week_start"].date().isoformat(),
                        exercise,
                        status,
                        float(row["e1rm"]),
                        float(row["p10"]),
                        float(row["p90"]),
                    )
                )

    alerts_df = pd.DataFrame(
        alerts,
        columns=[
            "week_start",
            "exercise",
            "alert_level",
            "actual_e1rm",
            "p10",
            "p90",
        ],
    )

    with conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                week_start TEXT,
                exercise TEXT,
                alert_level TEXT,
                actual_e1rm REAL,
                p10 REAL,
                p90 REAL
            )
            """
        )

        conn.execute("DELETE FROM alerts")

        alerts_df.to_sql(
            "alerts",
            conn,
            if_exists="append",
            index=False,
        )

    conn.close()

    print(f"Saved {len(alerts_df)} alerts.")


if __name__ == "__main__":
    main()

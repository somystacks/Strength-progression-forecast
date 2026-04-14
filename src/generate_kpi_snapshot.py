import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = "data/training.sqlite"
OUTPUT_PATH = Path("docs/kpi_snapshot.md")

conn = sqlite3.connect(DB_PATH)

weekly = pd.read_sql_query(
    "SELECT week_start, exercise, e1rm FROM weekly_e1rm",
    conn
)

bands = pd.read_sql_query(
    """
    SELECT week_start, exercise, scenario, p10, p50, p90
    FROM forecast_bands
    WHERE scenario = '75%'
    """,
    conn
)

conn.close()

weekly["week_start"] = pd.to_datetime(weekly["week_start"])
bands["week_start"] = pd.to_datetime(bands["week_start"])

latest_actual = (
    weekly.sort_values("week_start")
    .groupby("exercise", as_index=False)
    .tail(1)
)

last_forecast_week = bands["week_start"].max()

horizon = bands[bands["week_start"] == last_forecast_week].copy()

horizon["band_width"] = horizon["p90"] - horizon["p10"]

kpis = latest_actual.merge(
    horizon[["exercise", "week_start", "p50", "band_width"]],
    on="exercise",
)

kpis = kpis.rename(columns={
    "exercise": "Lift",
    "week_start_x": "Latest week",
    "e1rm": "Latest e1RM (kg)",
    "week_start_y": "Forecast horizon week",
    "p50": "Forecast p50 (kg)",
    "band_width": "Uncertainty width p90–p10 (kg)",
})

table = kpis[
    [
        "Lift",
        "Latest week",
        "Latest e1RM (kg)",
        "Forecast horizon week",
        "Forecast p50 (kg)",
        "Uncertainty width p90–p10 (kg)"
    ]
].copy()

numeric_cols = [
    "Latest e1RM (kg)",
    "Forecast p50 (kg)",
    "Uncertainty width p90–p10 (kg)"
]
table[numeric_cols] = table[numeric_cols].round(1)

markdown = table.to_markdown(index=False)

OUTPUT_PATH.write_text(markdown)

print("KPI snapshot written to docs/kpi_snapshot.md")

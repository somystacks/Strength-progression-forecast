from __future__ import annotations

import sqlite3
import pandas as pd

from config import DB_PATH, CSV_LATEST_PATH, ALLOWED_EXERCISES, REQUIRED_COLUMNS

CSV_PATH = CSV_LATEST_PATH


def main() -> None:
    print("ingest_sets.py started. This will read the CSV, validate and clean the data, and load it into a SQLite database.")
    if not CSV_PATH.exists():  # Check if the CSV file exists
        raise FileNotFoundError(f"CSV file not found at {CSV_PATH}")
    # Read the CSV file into a DataFrame (CSV_PATH)
    df = pd.read_csv(str(CSV_PATH))

    # Basic schema validation
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {missing}. Found columns: {list(df.columns)}")

    # Keep only required columns in a consistent order
    df = df[REQUIRED_COLUMNS].copy()

    # Clean types
    df["date"] = pd.to_datetime(df["date"], errors="raise").dt.date.astype(
        str)  # Store as string in YYYY-MM-DD format
    # Remove leading/trailing whitespace
    df["exercise"] = df["exercise"].astype(str).str.strip()
    df["weight_kg"] = pd.to_numeric(
        df["weight_kg"], errors="raise")  # Convert to float
    df["reps"] = pd.to_numeric(
        df["reps"], errors="raise").astype(int)  # Convert to int
    df["set_number"] = pd.to_numeric(
        df["set_number"], errors="raise").astype(int)  # Convert to int
    df["session_name"] = df["session_name"].astype(
        str).str.strip()  # Remove leading/trailing whitespace

    # Filter to main lifts only (by design for Phase 3)
    before = len(df)  # For logging purposes
    # Filter to main lifts
    df = df[df["exercise"].isin(ALLOWED_EXERCISES)].copy()
    after = len(df)  # For logging purposes
    if after == 0:
        raise ValueError(
            "After filtering to main lifts, there are 0 rows. Check exercises names in the CSV.")
    if after != before:
        # For logging purposes
        print(
            f"Filtered rows: {before} -> {after} (kept only {sorted(ALLOWED_EXERCISES)})")

    # Add a simple session_id (stable enough for Phase 3)
    # If you later export a true session_id, we can replace this.
    # Create a simple session_id by combining date and session_name. This is not perfect but should be stable for Phase 3.
    df["session_id"] = df["date"] + " | " + df["session_name"]

    # Create DB + table and load
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))

    rows = list(df[["date", "exercise", "weight_kg", "reps", "set_number", "session_name", "session_id"]]
                .itertuples(index=False, name=None))

    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                exercise TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                reps INTEGER NOT NULL,
                set_number INTEGER NOT NULL,
                session_name TEXT NOT NULL,
                session_id TEXT NOT NULL
            );
        """)

        # Enforce idempotency: one row per (date, session_name, exercise, set_number)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_sets_unique
            ON sets(date, session_name, exercise, set_number);
        """)

    with conn:
        conn.executemany("""
            INSERT OR REPLACE INTO sets
            (date, exercise, weight_kg, reps, set_number, session_name, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, rows)

    # Quick sanity check
    cur = conn.cursor()  # Create a cursor
    # Execute a simple query to count rows
    cur.execute("SELECT COUNT(*) FROM sets;")
    row_count = cur.fetchone()[0]  # Fetch the result
    # Log the number of rows loaded
    print(f"Loaded {row_count} set rows into {DB_PATH}.")

    # Execute a query to count rows per exercise
    cur.execute("SELECT exercise, COUNT(*) FROM sets GROUP BY exercise;")
    counts = cur.fetchall()  # Fetch the counts by exercise
    print("Counts by exercise:", counts)
    # Log the number of exercise groups (should be <= number of allowed exercises)
    print("Number of exercise groups:", len(counts))
    conn.close()  # Close the database connection


if __name__ == "__main__":  # Run the main function when this script is executed
    main()

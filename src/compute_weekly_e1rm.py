import os
import sqlite3
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO_ROOT, "data", "training.sqlite")


# Helper function to get the Monday of the week for a given date series
def week_start_monday(date_series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(date_series, errors="raise")  # Convert to datetime
    # Get Monday of the week and convert back to string
    return (dt - pd.to_timedelta(dt.dt.weekday, unit="D")).dt.date.astype(str)


def main():
    print("compute_weekly_e1rm.py started. This will compute the weekly E1RM for each exercise and load it into the database.")

    conn = sqlite3.connect(DB_PATH)
    # Read the sets data from the database
    df = pd.read_sql_query(
        "SELECT date, exercise, weight_kg, reps FROM sets;", conn)
    conn.close()  # Close the database connection after reading the data

    # Log the number of rows pulled from the database
    print("Rows pulled from DB:", len(df))
    # Log the first few rows of the data pulled from the database for verification
    print(df.head(5))

    # Block 2: Compute e1RM using the Epley formula
    # Epley formula: e1RM = weight * (1 + reps/30)
    df["e1rm"] = df["weight_kg"] * (1 + df["reps"] / 30.0)

    # Block 3: Compute weekly e1RM by exercise
    # Get the week start date (Monday) for each row
    # This will be used to group by week
    df["week_start"] = week_start_monday(df["date"])

    print("\nDate -> week_start (first 8 rows):")
    # Log the date and corresponding week_start for the first 8 rows
    print(df[["date", "week_start"]].head(8))

    print("\nFirst 5 rows with e1RM:")
    # Log the first 5 rows with e1RM
    print(df[["exercise", "weight_kg", "reps", "e1rm"]].head(5))

    # Block 4: Weekly max e1RM per lift (Option B + weekly aggregation)
    weekly = (
        df.groupby(["week_start", "exercise"], as_index=False)["e1rm"].max()
        .sort_values(["week_start", "exercise"])
    )
    print("\nWeekly max e1RM by lift:\n")  # Log the weekly max e1RM by lift
    print(weekly.to_string(index=False))

    # Save weekly results to the database
    conn = sqlite3.connect(DB_PATH)

    with conn:
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS weekly_e1rm (
                         week_start TEXT NOT NULL,
                         exercise TEXT NOT NULL,
                         e1rm REAL NOT NULL,
                         primary key (week_start, exercise)
                         );
                        """)
        conn.execute(
            # Clear existing data (idempotent for now)
            "DELETE FROM weekly_e1rm;")

        # Insert the weekly e1rm data into the table
        weekly.to_sql("weekly_e1rm", conn, if_exists="append", index=False)

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM weekly_e1rm;")
        # Log the number of rows saved in the weekly_e1rm table
        print("\nSaved rows in weekly_e1rm:", cur.fetchone()[0])

    conn.close()  # Close the database connection after saving the data


if __name__ == "__main__":  # Ensure main() is called when this script is run directly
    main()  # Call the main function to execute the script

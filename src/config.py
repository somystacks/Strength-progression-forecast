from __future__ import annotations

import os
from pathlib import Path

# Repo root = parent of /src
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

DB_PATH = DATA_DIR / "training.sqlite"
CSV_LATEST_PATH = RAW_DIR / "strong_sets_latest.csv"

ALLOWED_EXERCISES = {"Squat", "Bench Press", "Deadlift"}
REQUIRED_COLUMNS = ["date", "exercise", "weight_kg",
                    "reps", "set_number", "session_name"]

# Google Sheets env vars (used by pull script)
GSHEETS_CREDS = os.getenv("GSHEETS_CREDS", "")
GSHEETS_SPREADSHEET_ID = os.getenv("GSHEETS_SPREADSHEET_ID", "")
GSHEETS_RANGE = os.getenv("GSHEETS_RANGE", "")

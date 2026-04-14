import os
from pathlib import Path
from dotenv import load_dotenv

import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


def fetch_sheet(creds_path, spreadsheet_id, sheet_range):
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_range)
        .execute()
    )

    values = result.get("values", [])

    if not values:
        raise ValueError("No data returned from sheet")

    header = values[0]
    data = values[1:]
    df = pd.DataFrame(data, columns=header)
    return df


def main():

    creds = os.getenv("GSHEETS_CREDS")
    spreadsheet_id = os.getenv("GSHEETS_SPREADSHEET_ID")
    sheet_range = os.getenv("GSHEETS_RANGE")

    if not creds or not spreadsheet_id or not sheet_range:
        raise ValueError(
            "Missing required environment variables. Need GSHEETS_CREDS, GSHEETS_SPREADSHEET_ID, and GSHEETS_RANGE")

    df = fetch_sheet(creds, spreadsheet_id, sheet_range)

    expected = {
        "date",
        "exercise",
        "weight_kg",
        "reps",
        "set_number",
        "session_name"
    }
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing columns in sheet: {missing}. Found: {list(df.columns)}")

    output_path = Path("data/raw/strong_sets_latest.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)

    print(f"Pulled {len(df)} rows from Google Sheet to {output_path}")


if __name__ == "__main__":
    main()

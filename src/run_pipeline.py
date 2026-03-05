from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> None:  # type: ignore
    print(f"\n▶ Running: {' '.join(cmd)}")  # type: ignore
    result = subprocess.run(cmd, check=False)  # type: ignore
    if result.returncode != 0:
        raise SystemExit(
            # type: ignore
            f"❌ Command failed with code {result.returncode}: {' '.join(cmd)}")


def main() -> None:
    # USe the same Python executable that launched this script (important for conda environments consistency)
    py = sys.executable  # type: ignore

    run([py, "src/pull_google_sheet.py"])
    run([py, "src/ingest_sets.py"])
    run([py, "src/compute_weekly_e1rm.py"])
    run([py, "src/build_forecasts.py"])
    run([py, "src/generate_kpi_snapshot.py"])

    print("\n✅ Pipeline refresh complete: pull → ingest → weekly_e1rm → forecast_bands")


if __name__ == "__main__":
    main()

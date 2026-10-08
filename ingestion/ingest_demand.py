"""
Pulls hourly electricity demand for the CAISO balancing authority
(CISO = Northern & Central California grid operator) from the EIA v2 API
and loads it into the `raw_eia_demand` DuckDB table.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pandas as pd
from dotenv import load_dotenv

from eia_client import fetch_eia_series
from db import write_raw_table

load_dotenv()

RESPONDENT = os.environ.get("EIA_RESPONDENT", "CISO")
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "30"))


def period_bounds_hourly(lookback_days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    # EIA hourly period format: "YYYY-MM-DDTHH"
    return start.strftime("%Y-%m-%dT%H"), end.strftime("%Y-%m-%dT%H")


def run() -> None:
    start, end = period_bounds_hourly(LOOKBACK_DAYS)
    print(f"[demand] Fetching {RESPONDENT} hourly demand {start} -> {end}")

    rows = fetch_eia_series(
        route="electricity/rto/region-data",
        facets={"respondent": [RESPONDENT], "type": ["D"]},  # D = Demand
        frequency="hourly",
        start=start,
        end=end,
    )

    if not rows:
        print("[demand] No rows returned. Check EIA_API_KEY / date range.")
        return

    df = pd.DataFrame(rows)
    df = df.rename(
        columns={
            "period": "period",
            "respondent": "respondent",
            "respondent-name": "respondent_name",
            "type": "series_type",
            "type-name": "series_type_name",
            "value": "demand_mwh",
            "value-units": "value_units",
        }
    )
    df["loaded_at"] = pd.Timestamp.utcnow()

    n = write_raw_table("raw_eia_demand", df)
    print(f"[demand] Loaded {n} rows into raw_eia_demand")


if __name__ == "__main__":
    run()

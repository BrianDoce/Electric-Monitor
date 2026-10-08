"""
Pulls hourly generation-by-fuel-type for the CAISO balancing authority
(CISO) from the EIA v2 API and loads it into `raw_eia_fuel_mix`.

Fuel type codes include: SUN (solar), WND (wind), WAT (hydro), NG (natural
gas), NUC (nuclear), COL (coal), OTH (other/batteries/misc). This table is
what powers the renewable-mix KPIs in the marts layer.
"""
from __future__ import annotations

import os

import pandas as pd
from dotenv import load_dotenv

from eia_client import fetch_eia_series
from db import write_raw_table
from ingest_demand import period_bounds_hourly  # reuse the same window logic

load_dotenv()

RESPONDENT = os.environ.get("EIA_RESPONDENT", "CISO")
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "30"))


def run() -> None:
    start, end = period_bounds_hourly(LOOKBACK_DAYS)
    print(f"[fuel_mix] Fetching {RESPONDENT} hourly fuel mix {start} -> {end}")

    rows = fetch_eia_series(
        route="electricity/rto/fuel-type-data",
        facets={"respondent": [RESPONDENT]},
        frequency="hourly",
        start=start,
        end=end,
    )

    if not rows:
        print("[fuel_mix] No rows returned. Check EIA_API_KEY / date range.")
        return

    df = pd.DataFrame(rows)
    df = df.rename(
        columns={
            "period": "period",
            "respondent": "respondent",
            "respondent-name": "respondent_name",
            "fueltype": "fuel_type",
            "type-name": "fuel_type_name",
            "value": "generation_mwh",
            "value-units": "value_units",
        }
    )
    df["loaded_at"] = pd.Timestamp.utcnow()

    n = write_raw_table("raw_eia_fuel_mix", df)
    print(f"[fuel_mix] Loaded {n} rows into raw_eia_fuel_mix")


if __name__ == "__main__":
    run()

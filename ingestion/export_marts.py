"""
Exports dbt mart tables from DuckDB to Parquet files in data/marts/, so
Power BI (or Excel, or pandas) can load them with "Get Data > Parquet"
with no DuckDB driver required. Run this after `dbt run`.
"""
from __future__ import annotations

from pathlib import Path

from db import get_connection

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = REPO_ROOT / "data" / "marts"

MART_TABLES = [
    "mart_demand_weather_hourly",
    "mart_fuel_mix_daily",
    "mart_grid_daily_summary",
]

# dbt-duckdb puts mart models in a "main_marts" schema by default
# (schema prefix = profile target schema "main" + the +schema: marts config).
MART_SCHEMA = "main_marts"


def run() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    con = get_connection()
    try:
        for table in MART_TABLES:
            out_path = EXPORT_DIR / f"{table}.parquet"
            qualified = f'"{MART_SCHEMA}"."{table}"'
            try:
                con.execute(
                    f"COPY (SELECT * FROM {qualified}) TO '{out_path.as_posix()}' "
                    f"(FORMAT PARQUET)"
                )
                print(f"[export] Wrote {out_path}")
            except Exception as exc:  # noqa: BLE001
                print(f"[export] Skipped {table}: {exc}")
    finally:
        con.close()


if __name__ == "__main__":
    run()

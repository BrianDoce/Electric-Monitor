"""
Shared DuckDB connection helper. All ingestion scripts write "raw" tables
into a single local DuckDB file, which dbt then reads from as its sources.
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE_PATH = REPO_ROOT / "warehouse" / "electric_monitor.duckdb"


def get_connection() -> duckdb.DuckDBPyConnection:
    WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(WAREHOUSE_PATH))


def write_raw_table(table_name: str, df: pd.DataFrame) -> int:
    """
    Full-refresh write of a raw table: each pipeline run overwrites the
    rolling lookback window. Simple and correct for a portfolio-scale
    project; a production pipeline would do incremental/merge loads.
    """
    con = get_connection()
    try:
        con.register("df_tmp", df)
        con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df_tmp")
        con.unregister("df_tmp")
        return len(df)
    finally:
        con.close()

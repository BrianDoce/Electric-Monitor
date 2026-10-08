"""
Runs the full ingestion stage: demand, fuel mix, weather.
Usage: python ingestion/run_all.py
"""
from __future__ import annotations

import ingest_demand
import ingest_fuel_mix
import ingest_weather


def main() -> None:
    print("=== Electric-Monitor ingestion: CAISO / Northern California ===")
    ingest_demand.run()
    ingest_fuel_mix.run()
    ingest_weather.run()
    print("=== Ingestion complete ===")


if __name__ == "__main__":
    main()

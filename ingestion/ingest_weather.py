"""
Pulls hourly temperature for a Northern California point (default:
Sacramento, representative of the CAISO NorCal load zone) from the free
Open-Meteo API (no API key required) and loads it into `raw_weather`.

This powers the demand-vs-temperature correlation analysis that's a
classic utility load-forecasting use case.
"""
from __future__ import annotations

import os

import pandas as pd
import requests
from dotenv import load_dotenv

from db import write_raw_table

load_dotenv()

LAT = float(os.environ.get("WEATHER_LAT", "38.5816"))
LON = float(os.environ.get("WEATHER_LON", "-121.4944"))
LOCATION_NAME = os.environ.get("WEATHER_LOCATION_NAME", "Sacramento_NorCal")
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "30"))

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def run() -> None:
    past_days = min(LOOKBACK_DAYS, 92)  # Open-Meteo's supported max
    print(f"[weather] Fetching hourly temperature for {LOCATION_NAME} "
          f"(lat={LAT}, lon={LON}), past_days={past_days}")

    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "temperature_2m",
        "temperature_unit": "fahrenheit",
        "past_days": past_days,
        "forecast_days": 1,
        "timezone": "America/Los_Angeles",
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()

    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])

    if not times:
        print("[weather] No rows returned from Open-Meteo.")
        return

    df = pd.DataFrame({"ts_local": times, "temperature_f": temps})
    df["location"] = LOCATION_NAME
    df["latitude"] = LAT
    df["longitude"] = LON
    df["loaded_at"] = pd.Timestamp.utcnow()

    n = write_raw_table("raw_weather", df)
    print(f"[weather] Loaded {n} rows into raw_weather")


if __name__ == "__main__":
    run()

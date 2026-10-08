"""
Thin client for the EIA v2 API (https://www.eia.gov/opendata/).

Handles pagination and returns a flat list of row dicts. Free API key
required: https://www.eia.gov/opendata/register.php
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests

EIA_BASE_URL = "https://api.eia.gov/v2"
PAGE_SIZE = 5000


class EIAClientError(RuntimeError):
    pass


def fetch_eia_series(
    route: str,
    facets: dict[str, list[str]],
    frequency: str,
    start: str,
    end: str,
    api_key: str | None = None,
    max_retries: int = 3,
) -> list[dict[str, Any]]:
    """
    Fetch all rows for a given EIA v2 data route, paginating as needed.

    route: e.g. "electricity/rto/region-data" or "electricity/rto/fuel-type-data"
    facets: e.g. {"respondent": ["CISO"], "type": ["D"]}
    frequency: "hourly" | "daily" | "monthly"
    start/end: period strings matching the route's expected format
               (hourly -> "YYYY-MM-DDTHH", daily -> "YYYY-MM-DD")
    """
    api_key = api_key or os.environ.get("EIA_API_KEY")
    if not api_key or api_key == "your_eia_api_key_here":
        raise EIAClientError(
            "EIA_API_KEY is missing. Get a free key at "
            "https://www.eia.gov/opendata/register.php and put it in .env"
        )

    url = f"{EIA_BASE_URL}/{route}/data/"
    rows: list[dict[str, Any]] = []
    offset = 0
    total = None

    while total is None or offset < total:
        params: dict[str, Any] = {
            "api_key": api_key,
            "frequency": frequency,
            "data[]": "value",
            "start": start,
            "end": end,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": offset,
            "length": PAGE_SIZE,
        }
        for facet_name, facet_values in facets.items():
            params[f"facets[{facet_name}][]"] = facet_values

        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, params=params, timeout=60)
                resp.raise_for_status()
                break
            except requests.RequestException as exc:  # pragma: no cover
                last_err = exc
                time.sleep(2 * (attempt + 1))
        else:
            raise EIAClientError(f"EIA request failed after retries: {last_err}")

        payload = resp.json()
        response_block = payload.get("response", {})
        batch = response_block.get("data", [])
        rows.extend(batch)

        total = int(response_block.get("total", len(batch)))
        offset += PAGE_SIZE

        if not batch:
            break

    return rows

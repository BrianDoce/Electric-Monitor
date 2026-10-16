# CLAUDE.md

Grid reliability pipeline for CAISO / Northern California: EIA v2 + Open-Meteo -> DuckDB -> dbt -> Parquet -> Power BI. See `README.md` and `docs/architecture.md` for background.

## Commands

Run from the stated directory (scripts use relative paths and `DBT_PROFILES_DIR`).

- Install: `pip install -r requirements.txt`
- Ingest all (from `ingestion/`): `python run_all.py` (individual: `ingest_demand.py`, `ingest_fuel_mix.py`, `ingest_weather.py`)
- Transform (from `dbt/`): `dbt run`, `dbt test`, `dbt docs generate`
- Export marts to `data/marts/*.parquet` (from `ingestion/`): `python export_marts.py`
- Findings report (from repo root): `python reports/generate_findings.py` regenerates `docs/findings.md` from the marts; never edit that file by hand
- SQL agent (from repo root; needs `ANTHROPIC_API_KEY`, `pip install -r agents/requirements.txt`): `python agents/sql_agent.py "question"`; offline checks with `--schema` / `--sql`
- Anomaly agent (from repo root): `python agents/anomaly_agent.py [--days N --threshold Z]`; writes `docs/insights/<date>.md`, calls Claude only if something is flagged

CI (`.github/workflows/pipeline.yml`) runs the same sequence daily and on push to `main`, then deploys dbt docs to GitHub Pages.

## Config

Copy `.env.example` to `.env`. Needs `EIA_API_KEY`; also `EIA_RESPONDENT` (CISO), `WEATHER_LAT`/`WEATHER_LON`/`WEATHER_LOCATION_NAME` (Sacramento), `LOOKBACK_DAYS` (30). Never commit `.env`.

## Layout

- `ingestion/` — Python: `eia_client.py` (API client), `db.py` (DuckDB access), `ingest_*.py`, `export_marts.py`
- `dbt/models/staging/` — `stg_eia_demand`, `stg_eia_fuel_mix`, `stg_weather` (views)
- `dbt/models/marts/` — `mart_demand_weather_hourly`, `mart_fuel_mix_daily`, `mart_grid_daily_summary`
- `warehouse/` and `data/marts/` — generated outputs, not committed
- `reports/` — `generate_findings.py` (computes docs/findings.md from the marts)
- `agents/` — `sql_agent.py` (natural-language-to-SQL over the marts; read-only, SELECT-only); `anomaly_agent.py` (z-score detection, then a Claude-written note; runs in CI as a non-blocking step)

## Conventions

- Raw ingestion is a full refresh of a rolling window, not incremental. Keep it that way unless asked.
- Every new staging/mart model needs `not_null`/`unique` tests in the matching `_*__models.yml`, so bad pulls fail CI.
- Add new sources to `_staging__sources.yml`.

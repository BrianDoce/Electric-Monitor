# Electric-Monitor

A grid reliability & demand intelligence pipeline for Northern California,
built to show end-to-end data engineering and analytics skills aimed at
the utilities industry: free public APIs -> DuckDB -> dbt -> Power BI,
with an AI agent layer planned on top.

**Region**: CAISO (California Independent System Operator, EIA
respondent code `CISO`) — the balancing authority covering Northern and
Central California. Weather is sampled at Sacramento as a representative
Northern California point.

## Why this project

Utility analysts work with demand/load data, generation fuel mix, and
weather-driven load forecasting every day. This project pulls the same
category of data a CAISO or utility analyst would actually look at:

- Hourly electricity demand (MWh)
- Hourly generation by fuel type (solar, wind, hydro, gas, nuclear, etc.)
- Hourly temperature, to analyze the classic demand-vs-weather relationship
- Daily renewable-generation share, peak demand, and temperature extremes

See [`docs/architecture.md`](docs/architecture.md) for the full pipeline
diagram and design rationale.

## Stack

| Layer | Tool | Why |
|---|---|---|
| Ingestion | Python (`requests`, `pandas`) | Simple, testable, no framework overhead |
| Data sources | [EIA v2 API](https://www.eia.gov/opendata/) (free), [Open-Meteo](https://open-meteo.com/) (free, no key) | Real utility-grade data, zero cost |
| Warehouse | [DuckDB](https://duckdb.org/) | Free, file-based, works like a real analytical warehouse for dbt |
| Transform | [dbt-core](https://www.getdbt.com/) + dbt-duckdb | Tested, documented, versioned SQL models |
| Orchestration | GitHub Actions (free tier) | Daily scheduled runs, CI for data quality |
| BI | Power BI | Dashboards on top of exported Parquet marts |
| Docs | dbt docs -> GitHub Pages | Public, checkable data lineage artifact |
| AI agent (planned) | see [`agents/README.md`](agents/README.md) | NL-to-SQL + anomaly-summary agent, built after the data foundation |

## Project layout

```
ingestion/        Python scripts: pull from EIA + Open-Meteo into DuckDB
warehouse/        electric_monitor.duckdb (generated, gitignored)
dbt/              dbt project: staging models, marts, tests, docs
data/marts/       Parquet exports of the dbt marts, for Power BI (generated)
docs/             Architecture notes
agents/           Planned AI agent layer (not yet built)
.github/workflows/  Daily pipeline: ingest -> dbt run/test -> export -> docs
```

## Setup

1. **Get a free EIA API key**: https://www.eia.gov/opendata/register.php
2. Copy `.env.example` to `.env` and fill in `EIA_API_KEY`.
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run ingestion:
   ```
   cd ingestion
   python run_all.py
   ```
5. Run dbt (builds staging + mart models, runs tests):
   ```
   cd dbt
   dbt run
   dbt test
   ```
6. Export marts to Parquet for Power BI:
   ```
   cd ingestion
   python export_marts.py
   ```
7. In Power BI Desktop: **Get Data > Parquet**, point at the files in
   `data/marts/`. Start from `mart_grid_daily_summary.parquet` for
   top-level KPI cards and trend lines.

The GitHub Actions workflow (`.github/workflows/pipeline.yml`) runs this
same sequence daily and publishes the dbt docs site via GitHub Pages. To
enable it in your fork: add an `EIA_API_KEY` repository secret, and
enable GitHub Pages (Settings -> Pages -> Source: GitHub Actions).

## Data model

- `stg_eia_demand`, `stg_eia_fuel_mix`, `stg_weather` — cleaned, typed
  staging views.
- `mart_demand_weather_hourly` — hourly demand joined to temperature, with
  day-of-week/weekend flags, for load-forecasting-style analysis.
- `mart_fuel_mix_daily` — daily generation by fuel type with % share of
  total generation and a renewable/non-renewable flag.
- `mart_grid_daily_summary` — one row per day: peak/avg/min demand, max/avg
  temperature, renewable %. The primary table for dashboard KPIs.

Every staging and mart model has `not_null`/`unique` dbt tests, so a bad
API pull fails the pipeline instead of silently reaching the dashboard.

## Notes on scope

- Raw ingestion is a **full refresh of a rolling 30-day window**, not an
  incremental/append pipeline. This is a deliberate simplification for a
  portfolio-scale project; documented rather than hidden.
- The AI agent layer (NL-to-SQL querying and anomaly-summary generation)
  is the next milestone, intentionally built after the dbt foundation is
  solid — see [`agents/README.md`](agents/README.md).

# Architecture

```
            EIA v2 API              Open-Meteo API
      (CAISO / CISO demand &            (Sacramento,
       fuel-type generation)             Northern CA)
               |                             |
               v                             v
      ingestion/ingest_demand.py    ingestion/ingest_weather.py
      ingestion/ingest_fuel_mix.py
               |                             |
               +--------------+--------------+
                              v
                 warehouse/electric_monitor.duckdb
                 (raw_eia_demand, raw_eia_fuel_mix,
                  raw_weather)
                              |
                              v
                     dbt (staging -> marts)
                 stg_eia_demand, stg_eia_fuel_mix,
                 stg_weather
                              |
                              v
        mart_demand_weather_hourly  mart_fuel_mix_daily
                 mart_grid_daily_summary
                              |
               +--------------+--------------+
               v                              v
     ingestion/export_marts.py          dbt docs (lineage,
     -> data/marts/*.parquet              column docs, tests)
               |                              |
               v                              v
          Power BI dashboards          GitHub Pages site
```

## Why this shape

- **DuckDB as the warehouse**: free, file-based, zero infrastructure to
  stand up, and dbt-duckdb treats it exactly like a "real" cloud warehouse
  for modeling purposes.
- **Full-refresh raw loads**: each run re-pulls a rolling lookback window
  (default 30 days) rather than appending indefinitely. Simple, idempotent,
  and avoids duplicate/dedup logic that would be a distraction at this
  scale. Documented explicitly as a simplification, not hidden.
- **Parquet export step**: Power BI has no first-class DuckDB connector on
  Windows without extra ODBC setup. Exporting the mart tables to Parquet
  means "Get Data > Parquet" just works, and the files are still a
  genuine columnar format (not a CSV dump) you can also load with pandas.
- **dbt tests**: `not_null`/`unique` tests on staging and mart models are
  the project's data-quality gate. `dbt test` running in CI means a bad
  pull from a source API fails the pipeline loudly instead of silently
  corrupting a dashboard.
- **GitHub Actions + GitHub Pages**: the pipeline runs daily for free, and
  the generated dbt docs site is a public, checkable artifact of the data
  model and lineage.

## Region scope

CAISO (EIA respondent code `CISO`) is the California Independent System
Operator, the balancing authority for most of California including the
entire Northern California grid. Weather is sampled at Sacramento as a
representative Northern California point; the location is a single
`.env` change (`WEATHER_LAT` / `WEATHER_LON`) if you want to shift it or
average multiple cities later.

## AI agent layer

Two agents sit on top of the marts (see `agents/README.md`):

- `agents/sql_agent.py`: natural-language-to-SQL over the marts, read-only and
  SELECT-only, with the executed SQL shown alongside each answer.
- `agents/anomaly_agent.py`: deterministic z-score detection, then a
  Claude-written analyst note only when something is flagged. It runs in CI
  after the exports as a non-blocking step.

`reports/generate_findings.py` also computes `docs/findings.md` from the marts,
so reported figures are reproducible rather than hand-typed.

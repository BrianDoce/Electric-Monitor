# AI agent layer (planned, next milestone)

Intentionally not built yet. Per the project plan, the AI agent sits on
top of the dbt marts once they're solid — an agent layered onto messy
data looks worse than no agent at all.

Two concrete, scoped agents to build here next:

1. **Natural-language-to-SQL agent**: takes a question like "what was
   peak demand last week during the heat wave?", uses the dbt-generated
   schema/docs as grounding context, generates a SQL query against
   `mart_grid_daily_summary` / `mart_demand_weather_hourly`, runs it
   against the DuckDB warehouse, and returns the answer plus the query
   it ran (so it's checkable, not a black box).

2. **Anomaly/insight agent**: runs after each pipeline load (as a step in
   `.github/workflows/pipeline.yml`), scans `mart_grid_daily_summary` for
   demand spikes or renewable-share shifts beyond a threshold, and writes
   a short plain-English summary (e.g. to a `docs/insights/` markdown log
   or a GitHub issue/comment). This mirrors the actual job of a junior
   utility analyst: flag the anomaly and explain it.

Both are intentionally thin wrappers around the already-tested, already-
documented marts — the agent's value is explanation and interface, not
reinventing the data model.

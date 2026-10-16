# AI agent layer

The AI agents sit on top of the dbt marts, built only after the data
layer was tested and stable — an agent layered onto messy data looks worse
than no agent at all.

## 1. Natural-language-to-SQL agent (built): `sql_agent.py`

```
pip install -r agents/requirements.txt
export ANTHROPIC_API_KEY=...        # or put it in .env
python agents/sql_agent.py "What was peak demand on the hottest complete day?"
python agents/sql_agent.py --schema   # show the grounding context
python agents/sql_agent.py --sql "select * from mart_grid_daily_summary limit 5"
```

Claude (default `claude-opus-5-5`, override with `AGENT_MODEL`) gets the
mart descriptions from the dbt yml plus live column types from DuckDB, writes
SQL through a single `run_sql` tool, and answers. The SQL that ran is
printed after the answer so it can be checked. Guardrails: the warehouse is
opened read-only with filesystem access disabled, only a single
`SELECT`/`WITH` statement is accepted, and results are capped at 200 rows.

## 2. Anomaly/insight agent (planned)

Runs after each pipeline load (as a step in
   `.github/workflows/pipeline.yml`), scans `mart_grid_daily_summary` for
   demand spikes or renewable-share shifts beyond a threshold, and writes
   a short plain-English summary (e.g. to a `docs/insights/` markdown log
   or a GitHub issue/comment). This mirrors the actual job of a junior
   utility analyst: flag the anomaly and explain it.

Both are intentionally thin wrappers around the already-tested, already-
documented marts — the agent's value is explanation and interface, not
reinventing the data model.

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

## 2. Anomaly/insight agent (built): `anomaly_agent.py`

```
python agents/anomaly_agent.py                      # last 3 complete days, |z| >= 2
python agents/anomaly_agent.py --days 7 --threshold 1.5
```

Detection is deterministic: for each recent complete day it computes
leave-one-out z-scores for peak demand and renewable share, plus peak demand
relative to what that day's max temperature predicts (a regression on the
rest of the window). Only if something is flagged does Claude write a short
analyst note from the figures provided, with causes labelled as likely rather
than certain. No anomaly means no API call and no cost.

The note is written to `docs/insights/<date>.md`, printed, and appended to
the GitHub Actions job summary. In CI it runs as a non-blocking step after
the exports (needs an `ANTHROPIC_API_KEY` repo secret) and the notes are
included in the build artifact; CI does not commit them back.

Both are intentionally thin wrappers around the already-tested, already-
documented marts — the agent's value is explanation and interface, not
reinventing the data model.

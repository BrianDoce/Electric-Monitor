"""
Natural-language-to-SQL agent over the dbt marts.

Ask a question in plain English; Claude writes SQL against the mart tables
in the DuckDB warehouse, runs it (read-only), and answers. The SQL that was
run is always printed so the answer is checkable.

Usage (from repo root, after the pipeline has populated the warehouse):
    python agents/sql_agent.py "What was peak demand on the hottest day?"
    python agents/sql_agent.py --schema        # show the grounding context
    python agents/sql_agent.py --sql "select * from mart_grid_daily_summary limit 3"

Needs ANTHROPIC_API_KEY (env or .env) for questions; --schema/--sql do not.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import duckdb
import yaml
from anthropic import Anthropic, beta_tool
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "warehouse" / "electric_monitor.duckdb"
MARTS_YML = REPO_ROOT / "dbt" / "models" / "marts" / "_marts__models.yml"
MARTS_SCHEMA = "main_marts"
MAX_ROWS = 200

load_dotenv(REPO_ROOT / ".env")
MODEL = os.environ.get("AGENT_MODEL", "claude-opus-5-5")


def connect() -> duckdb.DuckDBPyConnection:
    """Read-only connection with filesystem/network access disabled."""
    con = duckdb.connect(
        str(DB_PATH), read_only=True, config={"enable_external_access": False}
    )
    con.execute(f"SET search_path = '{MARTS_SCHEMA}'")
    return con


def run_query(sql: str) -> str:
    """Run one SELECT/WITH statement and return a markdown table."""
    stmt = sql.strip().rstrip(";").strip()
    if ";" in stmt:
        return "Error: only a single statement is allowed."
    if not re.match(r"(?is)^(select|with)\b", stmt):
        return "Error: only SELECT or WITH queries are allowed."
    con = connect()
    try:
        cur = con.execute(stmt)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(MAX_ROWS + 1)
    except duckdb.Error as e:
        return f"SQL error: {e}"
    finally:
        con.close()

    truncated = len(rows) > MAX_ROWS
    rows = rows[:MAX_ROWS]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
    out = "\n".join(lines)
    if not rows:
        out += "\n(0 rows)"
    if truncated:
        out += f"\n(truncated to first {MAX_ROWS} rows)"
    return out


def schema_context() -> str:
    """Mart descriptions from the dbt yml, plus live column types from DuckDB."""
    models = yaml.safe_load(MARTS_YML.read_text(encoding="utf-8"))["models"]
    con = connect()
    parts = []
    try:
        for m in models:
            name = m["name"]
            parts.append(f"### {name}\n{m.get('description', '')}")
            notes = {c["name"]: c.get("description", "") for c in m.get("columns", [])}
            for col, typ, *_ in con.execute(f"DESCRIBE {name}").fetchall():
                note = f" - {notes[col]}" if notes.get(col) else ""
                parts.append(f"- {col} ({typ}){note}")
            parts.append("")
    finally:
        con.close()
    return "\n".join(parts)


SYSTEM_TEMPLATE = """\
You answer questions about California grid demand, generation mix and weather
by querying a DuckDB warehouse with the run_sql tool. The data is CAISO
(balancing authority CISO) hourly demand and fuel mix from the EIA, plus
hourly temperature at Sacramento, covering a rolling window of about 30 days.

Tables (the default schema is already set; refer to them by bare name):

{schema}

Conventions:
- Times in period_hour, date and hour_of_day are Pacific local time;
  period_hour_utc is UTC. Demand and generation are in MWh, temperature in F.
- pct_of_daily_generation and renewable_pct are on a 0-100 scale, not 0-1.
- The first and last days of the window are partial. Filter
  is_complete_day = true on mart_grid_daily_summary when comparing days or
  reporting daily min/average/renewable figures, and say when you did.
- Prefer mart_grid_daily_summary for daily questions, mart_fuel_mix_daily for
  fuel questions, mart_demand_weather_hourly for hourly or weather questions.

Rules:
- Only state numbers you got from a query. If the data cannot answer the
  question (for example history older than the window, or a forecast), say so
  plainly instead of guessing.
- If a query errors, read the message and fix it. Keep queries small.
- Give a short direct answer with the key figures. The SQL you ran is shown
  to the user separately, so do not repeat it.
"""


def ask(question: str) -> tuple[str, list[str]]:
    """Return (answer, queries_run)."""
    queries: list[str] = []

    @beta_tool
    def run_sql(query: str) -> str:
        """Run a single read-only SQL SELECT (or WITH) query against the grid
        marts in DuckDB and return the result as a markdown table. At most
        200 rows are returned.

        Args:
            query: A single DuckDB SQL SELECT statement.
        """
        queries.append(query.strip())
        return run_query(query)

    client = Anthropic()
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_TEMPLATE.format(schema=schema_context()),
        tools=[run_sql],
        messages=[{"role": "user", "content": question}],
    )
    final = None
    for message in runner:
        final = message
    if final is None:
        return "No response.", queries
    if final.stop_reason == "refusal":
        return "The model declined to answer this question.", queries
    text = "".join(b.text for b in final.content if b.type == "text").strip()
    return text or "No answer produced.", queries


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("question", nargs="?", help="question in plain English")
    p.add_argument("--schema", action="store_true", help="print grounding context and exit")
    p.add_argument("--sql", help="run one SQL query through the guarded path and exit")
    args = p.parse_args()

    if not DB_PATH.exists():
        sys.exit(f"Warehouse not found at {DB_PATH}. Run the pipeline first.")
    if args.schema:
        print(schema_context())
        return
    if args.sql:
        print(run_query(args.sql))
        return
    if not args.question:
        p.error("provide a question, or use --schema / --sql")

    answer, queries = ask(args.question)
    print(answer)
    if queries:
        print("\n--- SQL used ---")
        for i, q in enumerate(queries, 1):
            print(f"[{i}]\n{q}\n")


if __name__ == "__main__":
    main()

"""
Anomaly/insight agent.

Step 1 (deterministic): scan recent complete days in mart_grid_daily_summary
for unusual peak demand, renewable share, and demand that temperature does
not explain. Detection is plain statistics, so the model never decides
*whether* something is anomalous.
Step 2 (Claude): only if something was flagged, write a short analyst note
explaining it from the figures provided. No anomaly means no API call.

Usage (from repo root, after the pipeline has populated the warehouse):
    python agents/anomaly_agent.py
    python agents/anomaly_agent.py --days 7 --threshold 1.5

Writes docs/insights/<latest-date>.md, prints the note, and appends it to the
GitHub Actions job summary when run in CI. Needs ANTHROPIC_API_KEY only when
an anomaly is found.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd
from anthropic import Anthropic

from sql_agent import DB_PATH, MODEL, REPO_ROOT, connect

INSIGHTS_DIR = REPO_ROOT / "docs" / "insights"
MIN_BASELINE_DAYS = 10


def load_days(con) -> pd.DataFrame:
    df = con.execute(
        """
        select date, peak_demand_mwh, avg_demand_mwh, max_temp_f, renewable_pct
        from main_marts.mart_grid_daily_summary
        where is_complete_day and max_temp_f is not null and renewable_pct is not null
        order by date
        """
    ).df()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def detect(df: pd.DataFrame, recent_days: int, threshold: float) -> list[dict]:
    """Leave-one-out z-scores for each of the most recent complete days."""
    findings = []
    for idx in df.index[-recent_days:]:
        row = df.loc[idx]
        rest = df.drop(index=idx)

        # Peak demand and renewable share against the rest of the window.
        for col, label in [
            ("peak_demand_mwh", "peak demand (MWh)"),
            ("renewable_pct", "renewable share (%)"),
        ]:
            sd = rest[col].std()
            if sd and sd > 0:
                z = (row[col] - rest[col].mean()) / sd
                if abs(z) >= threshold:
                    findings.append(
                        dict(date=row["date"], metric=label, value=float(row[col]),
                             baseline=float(rest[col].mean()), z=float(z))
                    )

        # Peak demand that temperature does not explain (regression residual).
        slope, intercept = np.polyfit(rest["max_temp_f"], rest["peak_demand_mwh"], 1)
        resid = rest["peak_demand_mwh"] - (slope * rest["max_temp_f"] + intercept)
        expected = slope * row["max_temp_f"] + intercept
        sd = resid.std()
        if sd and sd > 0:
            z = (row["peak_demand_mwh"] - expected) / sd
            if abs(z) >= threshold:
                findings.append(
                    dict(date=row["date"], metric="peak demand vs. what max temperature predicts (MWh)",
                         value=float(row["peak_demand_mwh"]), baseline=float(expected), z=float(z))
                )
    return findings


def context_for(con, df: pd.DataFrame, dates: list) -> str:
    parts = []
    for d in dates:
        day = df[df["date"] == d].iloc[0]
        mix = con.execute(
            """
            select fuel_type_name, pct_of_daily_generation
            from main_marts.mart_fuel_mix_daily where date = ? order by 2 desc
            """,
            [d],
        ).fetchall()
        mix_s = ", ".join(f"{n} {p:.1f}%" for n, p in mix)
        parts.append(
            f"{d}: peak {day.peak_demand_mwh:,.0f} MWh, avg {day.avg_demand_mwh:,.0f} MWh, "
            f"max temp {day.max_temp_f:.1f}F, renewable {day.renewable_pct:.1f}%. "
            f"Fuel mix: {mix_s}"
        )
    base = df
    parts.append(
        f"Window baseline ({len(base)} complete days): peak demand mean "
        f"{base.peak_demand_mwh.mean():,.0f} MWh, renewable mean "
        f"{base.renewable_pct.mean():.1f}%, max temp mean {base.max_temp_f.mean():.1f}F."
    )
    return "\n".join(parts)


PROMPT = """\
You are a junior utility analyst writing a short note on California (CAISO)
grid anomalies. A statistical check flagged the items below (z = standard
deviations from the rest of the ~30-day window, leave-one-out). Explain what
happened using ONLY the figures provided. Where you suggest a cause, label it
as a likely explanation, not a fact; do not invent events, outages or prices.

Format: a one-line headline, then at most 5 concise bullets (what, how unusual,
likely driver from the data), then one line on what to watch next. Plain
markdown, no preamble.

Flagged:
{flags}

Context:
{context}
"""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--days", type=int, default=3, help="how many recent complete days to check")
    p.add_argument("--threshold", type=float, default=2.0, help="|z| needed to flag")
    args = p.parse_args()

    if not DB_PATH.exists():
        sys.exit(f"Warehouse not found at {DB_PATH}. Run the pipeline first.")

    con = connect()
    try:
        df = load_days(con)
        if len(df) < MIN_BASELINE_DAYS:
            sys.exit(f"Only {len(df)} complete days; need {MIN_BASELINE_DAYS} for a baseline.")
        latest = df["date"].iloc[-1]
        findings = detect(df, args.days, args.threshold)

        if not findings:
            note = (f"# Grid insights - {latest}\n\nNo anomalies in the last {args.days} complete "
                    f"days (|z| >= {args.threshold}).\n")
        else:
            flags = "\n".join(
                f"- {f['date']}: {f['metric']} = {f['value']:,.1f} vs {f['baseline']:,.1f} "
                f"typical (z = {f['z']:+.2f})" for f in findings
            )
            dates = sorted({f["date"] for f in findings})
            prompt = PROMPT.format(flags=flags, context=context_for(con, df, dates))
            resp = Anthropic().messages.create(
                model=MODEL, max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )
            body = "".join(b.text for b in resp.content if b.type == "text").strip()
            note = (f"# Grid insights - {latest}\n\n{body}\n\n---\n"
                    f"Flagged by statistics (|z| >= {args.threshold}):\n{flags}\n")
    finally:
        con.close()

    INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    out = INSIGHTS_DIR / f"{latest}.md"
    out.write_text(note, encoding="utf-8")
    print(note)
    print(f"[anomaly] wrote {out.relative_to(REPO_ROOT)}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(note + "\n")


if __name__ == "__main__":
    main()

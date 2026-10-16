"""
Generates docs/findings.md from the dbt marts so every figure is computed,
not typed. Re-run after each pipeline load (CI does this and attaches the
result to the build artifact and job summary).

Usage (from repo root):
    python reports/generate_findings.py
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "warehouse" / "electric_monitor.duckdb"
OUT_PATH = REPO_ROOT / "docs" / "findings.md"
INSIGHTS_DIR = REPO_ROOT / "docs" / "insights"
MIN_DAYS = 10


def md_table(df: pd.DataFrame) -> str:
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(map(str, row)) + " |")
    return "\n".join(lines)


def fmt_date(d) -> str:
    return pd.Timestamp(d).strftime("%b %-d") if os.name != "nt" else pd.Timestamp(d).strftime("%b %d").replace(" 0", " ")


def hour_label(h: int) -> str:
    h = int(h)
    return f"{(h % 12) or 12} {'am' if h < 12 else 'pm'}"


def main() -> None:
    if not DB_PATH.exists():
        sys.exit(f"Warehouse not found at {DB_PATH}. Run the pipeline first.")
    con = duckdb.connect(str(DB_PATH), read_only=True)

    d = con.execute(
        "select * from main_marts.mart_grid_daily_summary where is_complete_day order by date"
    ).df()
    d["date"] = pd.to_datetime(d["date"])
    if len(d) < MIN_DAYS:
        sys.exit(f"Only {len(d)} complete days; need {MIN_DAYS}.")

    h = con.execute("select * from main_marts.mart_demand_weather_hourly").df()
    h["date"] = pd.to_datetime(h["date"])
    h = h[h["date"].isin(d["date"])].dropna(subset=["temperature_f"])
    fm = con.execute("select * from main_marts.mart_fuel_mix_daily").df()
    fm["date"] = pd.to_datetime(fm["date"])
    fm = fm[fm["date"].isin(d["date"])]
    hf = con.execute(
        """
        select hour(period_hour) as hr, fuel_type, avg(generation_mwh) as g
        from main_staging.stg_eia_fuel_mix
        where cast(period_hour as date) in (select date from main_marts.mart_grid_daily_summary where is_complete_day)
        group by 1, 2
        """
    ).df().pivot(index="hr", columns="fuel_type", values="g")

    start, end, n = d["date"].min(), d["date"].max(), len(d)
    out = [f"# Findings: CAISO / Northern California, {fmt_date(start)} - {fmt_date(end)}, {end.year}\n"]
    out.append(
        f"*Generated {date.today()} by `reports/generate_findings.py` from the dbt marts. "
        f"Do not edit by hand; re-run the script.*\n\n"
        f"A snapshot of the {n} complete days in the rolling window (partial edge days "
        f"excluded via `is_complete_day`). Demand is EIA balancing-authority demand "
        f"(includes imports); generation figures are in-state generation only. You can "
        f"reproduce any number with the SQL agent (`python agents/sql_agent.py \"...\"`).\n"
    )

    # 1. Temperature and demand
    hi, lo = d.loc[d.peak_demand_mwh.idxmax()], d.loc[d.peak_demand_mwh.idxmin()]
    r_daily = d.peak_demand_mwh.corr(d.max_temp_f)
    s_daily = np.polyfit(d.max_temp_f, d.peak_demand_mwh, 1)[0]
    r_hour = h.demand_mwh.corr(h.temperature_f)
    s_hour = np.polyfit(h.temperature_f, h.demand_mwh, 1)[0]
    out.append("## 1. Temperature and demand\n")
    out.append(
        f"- Daily peak demand ranged from **{lo.peak_demand_mwh:,.0f} MWh** ({fmt_date(lo.date)}, "
        f"max {lo.max_temp_f:.1f} F) to **{hi.peak_demand_mwh:,.0f} MWh** ({fmt_date(hi.date)}, "
        f"max {hi.max_temp_f:.1f} F).\n"
        f"- Daily peak vs. daily max temperature: **r = {r_daily:.2f}**, about "
        f"**{s_daily:+,.0f} MWh of peak demand per +1 F**.\n"
        f"- Hourly demand vs. hourly temperature: **r = {r_hour:.2f}**, about "
        f"**{s_hour:+,.0f} MWh per +1 F**.\n"
        f"- Mean daily peak {d.peak_demand_mwh.mean():,.0f} MWh at a mean daily high of "
        f"{d.max_temp_f.mean():.1f} F.\n"
    )

    # 2. Load shape
    shape = h.groupby("hour_of_day").demand_mwh.mean()
    tr, pk = shape.idxmin(), shape.idxmax()
    out.append("## 2. Daily load shape\n")
    out.append(
        f"Average demand bottoms out at **{shape[tr] / 1000:.1f} GW at {hour_label(tr)}** and "
        f"peaks at **{shape[pk] / 1000:.1f} GW at {hour_label(pk)}** (Pacific time). "
        f"The afternoon hottest hour is not the daily peak hour.\n"
    )

    # 3. Duck curve
    hf = hf.reindex(range(24)).fillna(0)
    sun = hf["SUN"].clip(lower=0) if "SUN" in hf else pd.Series(0, index=hf.index)
    gas = hf["NG"] if "NG" in hf else pd.Series(0, index=hf.index)
    net = shape.reindex(range(24)) - sun
    t_min = int(net.idxmin())
    after = net.loc[t_min:]
    t_max = int(after.idxmax())
    ramp, hrs = after.max() - net.min(), t_max - t_min
    rows = []
    for hr in sorted({t_min, 15, 18, t_max}):
        rows.append(
            dict(Hour=hour_label(hr), **{
                "Demand (GW)": f"{shape[hr] / 1000:.1f}",
                "Solar (GW)": f"{sun[hr] / 1000:.1f}",
                "Demand minus solar (GW)": f"{net[hr] / 1000:.1f}",
                "Gas (GW)": f"{gas[hr] / 1000:.1f}",
            })
        )
    out.append("## 3. The duck curve\n")
    out.append(
        "Subtracting solar from demand hour by hour on an average day (a simplified net "
        "load that ignores imports and storage):\n\n" + md_table(pd.DataFrame(rows)) + "\n\n"
        f"Net load climbs about **{ramp / 1000:.1f} GW in {hrs} hours** "
        f"({hour_label(t_min)} to {hour_label(t_max)}) as solar fades while demand stays high; "
        f"gas output goes from {gas[t_min] / 1000:.1f} GW to {gas[t_max] / 1000:.1f} GW over the "
        f"same hours.\n"
    )

    # 4. Weekday vs weekend
    wk = h.groupby("is_weekend").demand_mwh.mean()
    n_we = h[h.is_weekend].date.nunique()
    bands = pd.cut(h.temperature_f, [-100, 60, 70, 80, 90, 200],
                   labels=["<=60 F", "60-70 F", "70-80 F", "80-90 F", ">90 F"])
    tb = h.assign(band=bands).groupby(["band", "is_weekend"], observed=True).demand_mwh.mean().unstack()
    tb = tb.rename(columns={False: "Weekday (GW)", True: "Weekend (GW)"}) / 1000
    tb["Gap (GW)"] = tb["Weekday (GW)"] - tb["Weekend (GW)"]
    tb = tb.round(1).reset_index().rename(columns={"band": "Temperature"})
    out.append("## 4. Weekdays vs. weekends\n")
    if True in wk.index and False in wk.index:
        out.append(
            f"Average hourly demand was **{wk[False] / 1000:.1f} GW on weekdays vs. "
            f"{wk[True] / 1000:.1f} GW on weekends** ({(1 - wk[True] / wk[False]) * 100:.0f}% lower). "
            f"By temperature band:\n\n" + md_table(tb) + f"\n\nThe weekend sample is {n_we} days, "
            f"so treat gaps as suggestive.\n"
        )
    else:
        out.append("Not enough weekend and weekday days in the window to compare.\n")

    # 5. Renewable share
    d["week"] = d["date"] - pd.to_timedelta(d["date"].dt.weekday, unit="D")
    wkly = d.groupby("week").agg(days=("date", "count"), renewable=("renewable_pct", "mean"),
                                 peak=("peak_demand_mwh", "mean"), tmax=("max_temp_f", "mean"))
    wt = pd.DataFrame({
        "Week of": [fmt_date(i) for i in wkly.index],
        "Days": wkly["days"].values,
        "Renewable share (%)": wkly["renewable"].round(1).values,
        "Avg daily peak (GW)": (wkly["peak"] / 1000).round(1).values,
        "Avg daily high (F)": wkly["tmax"].round(1).values,
    })
    r_ren = d.renewable_pct.corr(d.peak_demand_mwh)
    k = min(7, n // 3)
    dates_sorted = sorted(d["date"])
    first = fm[fm.date.isin(dates_sorted[:k])].groupby("fuel_type_name").pct_of_daily_generation.mean()
    last = fm[fm.date.isin(dates_sorted[-k:])].groupby("fuel_type_name").pct_of_daily_generation.mean()
    allw = fm.groupby("fuel_type_name").pct_of_daily_generation.mean()
    mix = pd.DataFrame({"Whole window (%)": allw, f"First {k} days (%)": first,
                        f"Last {k} days (%)": last}).sort_values("Whole window (%)", ascending=False).round(1)
    mix = mix.reset_index().rename(columns={"fuel_type_name": "Fuel"})
    out.append("## 5. Renewable share and the fuel mix\n")
    out.append(
        f"Renewable share vs. daily peak demand: **r = {r_ren:.2f}**. Weekly view "
        f"(weeks with fewer than 7 complete days are partial):\n\n" + md_table(wt) + "\n\n"
        f"Share of generation by fuel:\n\n" + md_table(mix) + "\n"
    )

    # 6. Latest anomaly note
    notes = sorted(INSIGHTS_DIR.glob("*.md")) if INSIGHTS_DIR.exists() else []
    out.append("## 6. Latest anomaly agent note\n")
    out.append(
        f"See [`docs/insights/{notes[-1].name}`](insights/{notes[-1].name}).\n" if notes
        else "No anomaly notes yet.\n"
    )

    # Caveats
    neg = fm[fm.fuel_type_name == "Other"].pct_of_daily_generation.min() if (fm.fuel_type_name == "Other").any() else 0
    out.append("## Caveats\n")
    out.append(
        f"- **Short window.** {n} complete days is a slice of one season; it says nothing about "
        f"other seasons, and a handful of days can drive a result.\n"
        f"- **Correlation, not causation.** Temperature, day of week, solar output and renewable "
        f"share move together; these fits do not separate them.\n"
        f"- **One weather point.** Temperature is Sacramento only, not a load-weighted average of "
        f"California.\n"
        f"- **Net load is approximate.** It subtracts in-state solar from demand that includes "
        f"imports, and ignores storage.\n"
        f"- **Negative \"Other\" generation.** EIA's \"Other\" category reaches {neg:.1f}% of daily "
        f"generation on some days, likely storage charging or accounting offsets, which slightly "
        f"distorts fuel shares.\n"
    )

    OUT_PATH.write_text("\n".join(out), encoding="utf-8")
    print(f"[findings] wrote {OUT_PATH.relative_to(REPO_ROOT)} ({n} complete days, {start.date()} to {end.date()})")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()

# Findings: CAISO / Northern California, Sep 17 - Oct 15, 2026

*Generated 2026-10-16 by `reports/generate_findings.py` from the dbt marts. Do not edit by hand; re-run the script.*

A snapshot of the 29 complete days in the rolling window (partial edge days excluded via `is_complete_day`). Demand is EIA balancing-authority demand (includes imports); generation figures are in-state generation only. You can reproduce any number with the SQL agent (`python agents/sql_agent.py "..."`).

## 1. Temperature and demand

- Daily peak demand ranged from **27,082 MWh** (Oct 11, max 75.0 F) to **46,213 MWh** (Oct 5, max 98.6 F).
- Daily peak vs. daily max temperature: **r = 0.85**, about **+564 MWh of peak demand per +1 F**.
- Hourly demand vs. hourly temperature: **r = 0.84**, about **+354 MWh per +1 F**.
- Mean daily peak 35,387 MWh at a mean daily high of 87.7 F.

## 2. Daily load shape

Average demand bottoms out at **23.7 GW at 5 am** and peaks at **34.7 GW at 6 pm** (Pacific time). The afternoon hottest hour is not the daily peak hour.

## 3. The duck curve

Subtracting solar from demand hour by hour on an average day (a simplified net load that ignores imports and storage):

| Hour | Demand (GW) | Solar (GW) | Demand minus solar (GW) | Gas (GW) |
|---|---|---|---|---|
| 11 am | 32.3 | 17.1 | 15.2 | 5.7 |
| 3 pm | 33.2 | 16.8 | 16.5 | 6.6 |
| 6 pm | 34.7 | 7.0 | 27.7 | 10.1 |
| 7 pm | 34.5 | 0.7 | 33.8 | 10.9 |

Net load climbs about **18.6 GW in 8 hours** (11 am to 7 pm) as solar fades while demand stays high; gas output goes from 5.7 GW to 10.9 GW over the same hours.

## 4. Weekdays vs. weekends

Average hourly demand was **30.5 GW on weekdays vs. 28.6 GW on weekends** (6% lower). By temperature band:

| Temperature | Weekday (GW) | Weekend (GW) | Gap (GW) |
|---|---|---|---|
| <=60 F | 24.5 | 24.3 | 0.1 |
| 60-70 F | 28.9 | 27.6 | 1.3 |
| 70-80 F | 32.3 | 30.2 | 2.1 |
| 80-90 F | 35.6 | 33.9 | 1.7 |
| >90 F | 38.2 | 38.0 | 0.2 |

The weekend sample is 8 days, so treat gaps as suggestive.

## 5. Renewable share and the fuel mix

Renewable share vs. daily peak demand: **r = -0.80**. Weekly view (weeks with fewer than 7 complete days are partial):

| Week of | Days | Renewable share (%) | Avg daily peak (GW) | Avg daily high (F) |
|---|---|---|---|---|
| Sep 14 | 4 | 65.1 | 31.4 | 83.4 |
| Sep 21 | 7 | 57.4 | 34.1 | 85.3 |
| Sep 28 | 7 | 50.4 | 38.7 | 93.4 |
| Oct 5 | 7 | 45.2 | 38.9 | 90.9 |
| Oct 12 | 4 | 57.5 | 29.5 | 80.4 |

Share of generation by fuel:

| Fuel | Whole window (%) | First 7 days (%) | Last 7 days (%) |
|---|---|---|---|
| Natural Gas | 38.2 | 27.6 | 38.7 |
| Solar | 29.9 | 36.2 | 27.3 |
| Wind | 11.1 | 13.2 | 15.5 |
| Hydro | 9.3 | 9.6 | 8.9 |
| Nuclear | 9.2 | 10.5 | 7.2 |
| Geothermal | 3.6 | 3.9 | 3.9 |
| Petroleum | 0.1 | 0.1 | 0.1 |
| Coal | 0.0 | 0.0 | -0.0 |
| Other | -1.3 | -1.1 | -1.6 |

## 6. Latest anomaly agent note

See [`docs/insights/2026-10-15.md`](insights/2026-10-15.md).

## Caveats

- **Short window.** 29 complete days is a slice of one season; it says nothing about other seasons, and a handful of days can drive a result.
- **Correlation, not causation.** Temperature, day of week, solar output and renewable share move together; these fits do not separate them.
- **One weather point.** Temperature is Sacramento only, not a load-weighted average of California.
- **Net load is approximate.** It subtracts in-state solar from demand that includes imports, and ignores storage.
- **Negative "Other" generation.** EIA's "Other" category reaches -3.7% of daily generation on some days, likely storage charging or accounting offsets, which slightly distorts fuel shares.

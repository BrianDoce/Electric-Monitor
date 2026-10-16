# Findings: CAISO / Northern California, Sep 17 - Oct 15, 2026

A snapshot of what the pipeline's marts show for the 29 complete days in the
30-day window (partial edge days excluded via `is_complete_day`). Figures are
reproducible from `data/marts/` or by asking the SQL agent
(`python agents/sql_agent.py "..."`). Demand is EIA balancing-authority demand
(which includes imports); generation figures are in-state generation only.

## 1. Temperature explains most of the swing in demand

- Daily peak demand ranged from **27,082 MWh** (Oct 11, max 75 F) to
  **46,213 MWh** (Oct 5, max 98.6 F).
- Daily peak vs. daily max temperature: **r = 0.85**. A straight-line fit gives
  roughly **+560 MWh of peak demand per +1 F** of daily max temperature.
- Hourly demand vs. hourly temperature: **r = 0.84**, about **+350 MWh per +1 F**.
- Mean daily peak was 35,387 MWh at a mean daily high of 87.7 F, which is warm
  for October. A cool spell in mid-October cut weekly average peaks by about
  a quarter (38.9 GW to 29.5 GW).

## 2. The daily load shape: early-morning trough, early-evening peak

Average demand across the window bottoms out at **~23.7 GW at 5 am** and peaks
at **~34.6 GW at 6 pm** Pacific, with a plateau of about 32-33 GW from 10 am to
3 pm. The evening peak arrives as solar fades, not
at the hottest hour of the afternoon (when solar is still at full output).

## 3. The duck curve is visible in the data

Subtracting solar from demand hour by hour (average day, a simplified net load
that ignores imports and storage):

| Hour (Pacific) | Demand (GW) | Solar (GW) | Demand minus solar (GW) |
|---|---|---|---|
| 11 am | 32.4 | 17.2 | **15.1** (daily minimum) |
| 3 pm | 33.1 | 16.8 | 16.3 |
| 6 pm | 34.6 | 7.1 | 27.5 |
| 7 pm | 34.4 | 0.7 | **33.7** |

Net load climbs about **18.5 GW in 8 hours** (11 am to 7 pm) as solar fades
while demand stays high. Natural gas fills the gap: its average output more than
doubles from ~5.6 GW at 11 am to ~10.8 GW at 7 pm. This is the classic
evening-ramp problem that grid operators plan around.

## 4. Weekends run lower, but the gap closes in the heat

Average hourly demand was **30.4 GW on weekdays vs. 28.6 GW on weekends** (about
6% lower). Comparing like temperatures, the weekday gap is ~1-2 GW below 90 F and
essentially vanishes above 90 F (38.2 vs. 38.0 GW), consistent with cooling load
dominating on hot days regardless of the calendar. The weekend sample is small
(8 days), so treat this as suggestive.

## 5. Renewable share fell as demand rose, then recovered

- Weekly average renewable share: **65%** (week of Sep 17) to **45%** (mid-Oct
  heat) and back to **57%** after the cool spell.
- Renewable share vs. daily peak demand: **r = -0.80**. When demand surges,
  the extra load is met mostly by gas, not by more renewables.
- First 7 vs. last 7 complete days (share of generation): natural gas
  **27.6% -> 38.7%**, solar **36.2% -> 27.3%**, nuclear **10.5% -> 7.2%**,
  wind **13.2% -> 15.5%**. Shorter autumn days plausibly explain some of the
  solar decline; the data doesn't say why nuclear dropped.
- Over the whole window gas averaged **37.6%** of generation, solar **30.6%**,
  wind **11.1%**, nuclear and hydro about **9.2%** each.

## 6. What the anomaly agent flagged

On Oct 15 peak demand was ~18% below what that day's 91.9 F high would predict
(z = -2.5); see `docs/insights/2026-10-15.md`. The note proposes, without
confirming, that solar suppressing measured demand or a brief heat spike could
explain it.

## Caveats

- **Short window.** 30 days is one slice of autumn. It says nothing about
  summer peaks or winter loads, and a handful of days drive several results.
- **Correlation, not causation.** Temperature, day of week, solar output and
  renewable share all move together; the fits above do not separate them.
- **One weather point.** Temperature is Sacramento only, not a load-weighted
  average of California.
- **Net load is approximate.** It subtracts in-state solar from demand that
  includes imports, and ignores storage.
- **Negative "Other" generation.** The EIA "Other" category dips below zero on
  several days (down to about -3%), likely net storage charging or accounting
  offsets, so fuel shares are slightly distorted.

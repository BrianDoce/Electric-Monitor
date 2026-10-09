# Power BI dashboard guide

Build the dashboard in Power BI Desktop (Windows) on top of the Parquet marts. Generate them first:

```
cd ingestion && python run_all.py
cd ../dbt && dbt run && dbt test
cd ../ingestion && python export_marts.py
```

## 1. Load the data

**Home > Get Data > Parquet**, then select all three files in `data/marts/`:

| File | Grain | Rows (30-day window) |
|---|---|---|
| `mart_grid_daily_summary.parquet` | 1 row per day | ~31 |
| `mart_fuel_mix_daily.parquet` | 1 row per day x fuel type | ~279 |
| `mart_demand_weather_hourly.parquet` | 1 row per hour | ~721 |

Use a relative-path parameter (**Transform data > Manage Parameters**, `MartsFolder`) so the report survives moving the repo. The files are overwritten on each export, so **Refresh** picks up new data.

### Schema notes

| Column | Type | Note |
|---|---|---|
| `date` | Date | Present in all three tables; the join key |
| `period_hour` | Date/Time | Hourly grain, no time zone (see caveats) |
| `*_pct`, `pct_of_daily_generation` | Decimal | Already on a **0-100** scale, not 0-1. Format as number, not percentage, or divide by 100 first |
| `is_renewable`, `is_weekend` | True/False | Good as slicers |
| `fuel_type` | Text | EIA code (SUN, WND...); use `fuel_type_name` for display |
| `respondent` | Text | Always `CISO`; hide it |

## 2. Model

In **Model view**, create one-to-many relationships (single direction, filter flows from the daily table):

- `mart_grid_daily_summary[date]` 1 -> * `mart_fuel_mix_daily[date]`
- `mart_grid_daily_summary[date]` 1 -> * `mart_demand_weather_hourly[date]`

Then add a Date table for proper time intelligence if you want one (`Calendar = CALENDARAUTO()`), and relate it to `mart_grid_daily_summary[date]`. Mark it as the date table. At 30 days of data this is optional.

Hide `respondent`, `total_generation_mwh`, and `fuel_type` (keep `fuel_type_name`).

## 3. Measures

Create in a `_Measures` table (**Home > Enter Data**, blank, then add measures):

```dax
Peak Demand (MWh) = MAX ( mart_grid_daily_summary[peak_demand_mwh] )

Avg Demand (MWh) = AVERAGE ( mart_grid_daily_summary[avg_demand_mwh] )

Max Temp (F) = MAX ( mart_grid_daily_summary[max_temp_f] )

Renewable % =
DIVIDE (
    SUMX (
        FILTER ( mart_fuel_mix_daily, mart_fuel_mix_daily[is_renewable] ),
        mart_fuel_mix_daily[generation_mwh]
    ),
    SUM ( mart_fuel_mix_daily[generation_mwh] )
)   -- format as Percentage

Solar % =
DIVIDE (
    CALCULATE ( SUM ( mart_fuel_mix_daily[generation_mwh] ),
                mart_fuel_mix_daily[fuel_type_name] = "Solar" ),
    SUM ( mart_fuel_mix_daily[generation_mwh] )
)

Peak vs 7-Day Avg =
VAR _today = MAX ( mart_grid_daily_summary[date] )
VAR _avg7 =
    CALCULATE (
        AVERAGE ( mart_grid_daily_summary[peak_demand_mwh] ),
        DATESINPERIOD ( mart_grid_daily_summary[date], _today, -7, DAY )
    )
RETURN DIVIDE ( [Peak Demand (MWh)] - _avg7, _avg7 )

Temp-Demand Correlation =
-- hourly grain; use on a card or tooltip
VAR _t = mart_demand_weather_hourly
RETURN
DIVIDE (
    SUMX ( _t, ( [temperature_f] - AVERAGEX ( _t, [temperature_f] ) )
             * ( [demand_mwh]    - AVERAGEX ( _t, [demand_mwh] ) ) ),
    SQRT (
        SUMX ( _t, ( [temperature_f] - AVERAGEX ( _t, [temperature_f] ) ) ^ 2 )
      * SUMX ( _t, ( [demand_mwh]    - AVERAGEX ( _t, [demand_mwh] ) ) ^ 2 )
    )
)
```

Because `Renewable %` is computed from generation sums, it aggregates correctly over any date range. Do not average the daily `renewable_pct` column across days.

## 4. Pages

**Page 1: Grid overview** (source: `mart_grid_daily_summary`)
- KPI cards: latest Peak Demand, Avg Demand, Max Temp, Renewable %, Peak vs 7-Day Avg.
- Line chart: `date` vs peak and avg demand.
- Line chart: `date` vs `Renewable %`.
- Date range slicer.

**Page 2: Demand vs weather** (source: `mart_demand_weather_hourly`)
- Scatter: X `temperature_f`, Y `demand_mwh`, color by `is_weekend`. Add a trend line (Analytics pane).
- Line + column: hourly `demand_mwh` with `temperature_f` on a secondary axis.
- Column chart: average demand by `hour_of_day` (the daily load shape), with `is_weekend` as a slicer.
- Card: `Temp-Demand Correlation`.

**Page 3: Fuel mix** (source: `mart_fuel_mix_daily`)
- 100% stacked area: `date` vs `generation_mwh` by `fuel_type_name`.
- Donut or bar: share by fuel type for the selected range.
- Slicer on `is_renewable`.
- Tip: the Solar share over the day is the interesting story (the duck curve); hourly fuel data is not in the mart yet, so this stays daily for now.

Use one consistent color per fuel type, and set the theme to match your dbt docs / README screenshots.

## 5. Data caveats to be aware of

- **Partial days at the window edges.** The rolling 30-day pull starts and ends mid-day, so those days have fewer than 24 hours. `mart_grid_daily_summary` has `hours_reported` and `is_complete_day`; add a page-level filter `is_complete_day = True` on Pages 1 and 3 so min/avg demand and renewable share are comparable.
- **Time zone.** EIA periods are UTC; staging converts them to Pacific so they align with the weather data, and `period_hour` / `hour_of_day` are Pacific local time. Around the November DST change the repeated 1 am hour can break the `unique` test on `period_hour`; handle that when it comes up.
- **Small sample.** 30 days is enough for a demo but not for seasonality. Say so in the dashboard footer.

## 6. Save

Save the report as `powerbi/Electric-Monitor.pbix` and add exported page screenshots to `docs/img/` for the README. `.pbix` files can be large; check the size before committing.

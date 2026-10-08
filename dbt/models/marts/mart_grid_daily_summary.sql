-- Executive-summary grain: one row per day, blending demand, weather,
-- and renewable share. This is the table most Power BI KPI cards/trend
-- lines should point at.

with demand_daily as (

    select
        date_trunc('day', period_hour) as date,
        max(demand_mwh) as peak_demand_mwh,
        avg(demand_mwh) as avg_demand_mwh,
        min(demand_mwh) as min_demand_mwh

    from {{ ref('stg_eia_demand') }}
    group by 1

),

weather_daily as (

    select
        date_trunc('day', period_hour) as date,
        max(temperature_f) as max_temp_f,
        avg(temperature_f) as avg_temp_f

    from {{ ref('stg_weather') }}
    group by 1

),

renewable_share as (

    select
        date,
        sum(case when is_renewable then generation_mwh else 0 end)
            / sum(generation_mwh) * 100 as renewable_pct

    from {{ ref('mart_fuel_mix_daily') }}
    group by 1

)

select
    demand_daily.date,
    demand_daily.peak_demand_mwh,
    demand_daily.avg_demand_mwh,
    demand_daily.min_demand_mwh,
    weather_daily.max_temp_f,
    weather_daily.avg_temp_f,
    round(renewable_share.renewable_pct, 2) as renewable_pct

from demand_daily
left join weather_daily using (date)
left join renewable_share using (date)
order by demand_daily.date

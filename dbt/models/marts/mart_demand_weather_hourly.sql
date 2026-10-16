-- Hourly grain: CAISO demand joined to Northern California temperature.
-- Powers the classic utility load-forecasting chart: demand vs. temperature.

with demand as (

    select * from {{ ref('stg_eia_demand') }}

),

weather as (

    select * from {{ ref('stg_weather') }}

)

select
    demand.period_hour_utc,
    demand.period_hour,
    demand.respondent,
    demand.demand_mwh,
    weather.temperature_f,
    date_trunc('day', demand.period_hour) as date,
    extract(hour from demand.period_hour) as hour_of_day,
    strftime(demand.period_hour, '%A') as day_of_week,
    case
        when extract(dow from demand.period_hour) in (0, 6) then true
        else false
    end as is_weekend

from demand
left join weather
    on demand.period_hour_utc = weather.period_hour_utc

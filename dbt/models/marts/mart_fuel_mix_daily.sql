-- Daily grain: generation by fuel type with % share of total generation.
-- Powers the renewable-vs-fossil generation mix chart.

with fuel_mix as (

    select * from {{ ref('stg_eia_fuel_mix') }}

),

daily_by_fuel as (

    select
        date_trunc('day', period_hour) as date,
        fuel_type,
        fuel_type_name,
        is_renewable,
        sum(generation_mwh) as generation_mwh

    from fuel_mix
    group by 1, 2, 3, 4

),

daily_totals as (

    select
        date,
        sum(generation_mwh) as total_generation_mwh

    from daily_by_fuel
    group by 1

)

select
    daily_by_fuel.date,
    daily_by_fuel.fuel_type,
    daily_by_fuel.fuel_type_name,
    daily_by_fuel.is_renewable,
    daily_by_fuel.generation_mwh,
    daily_totals.total_generation_mwh,
    round(
        daily_by_fuel.generation_mwh / daily_totals.total_generation_mwh * 100,
        2
    ) as pct_of_daily_generation

from daily_by_fuel
join daily_totals using (date)

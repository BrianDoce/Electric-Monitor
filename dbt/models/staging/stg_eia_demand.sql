with source as (

    select * from {{ source('raw', 'raw_eia_demand') }}

),

cleaned as (

    select
        -- EIA periods are UTC; convert to Pacific so they align with
        -- stg_weather (Open-Meteo ts_local is America/Los_Angeles).
        timezone('America/Los_Angeles', strptime(period, '%Y-%m-%dT%H') at time zone 'UTC') as period_hour,
        respondent,
        respondent_name,
        cast(demand_mwh as double) as demand_mwh,
        loaded_at

    from source
    where demand_mwh is not null

)

select * from cleaned

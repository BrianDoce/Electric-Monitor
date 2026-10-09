with source as (

    select * from {{ source('raw', 'raw_eia_fuel_mix') }}

),

cleaned as (

    select
        -- EIA periods are UTC; convert to Pacific so they align with
        -- stg_weather (Open-Meteo ts_local is America/Los_Angeles).
        timezone('America/Los_Angeles', strptime(period, '%Y-%m-%dT%H') at time zone 'UTC') as period_hour,
        respondent,
        respondent_name,
        fuel_type,
        fuel_type_name,
        cast(generation_mwh as double) as generation_mwh,
        case
            when fuel_type in ('SUN', 'WND', 'WAT', 'GEO', 'BIO')
                then true
            else false
        end as is_renewable,
        loaded_at

    from source
    where generation_mwh is not null

)

select * from cleaned

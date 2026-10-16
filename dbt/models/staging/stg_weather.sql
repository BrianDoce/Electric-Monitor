with source as (

    select * from {{ source('raw', 'raw_weather') }}

),

cleaned as (

    select
        strptime(ts_utc, '%Y-%m-%dT%H:%M') as period_hour_utc,
        timezone('America/Los_Angeles', strptime(ts_utc, '%Y-%m-%dT%H:%M') at time zone 'UTC') as period_hour,
        location,
        latitude,
        longitude,
        cast(temperature_f as double) as temperature_f,
        loaded_at

    from source
    where temperature_f is not null

)

select * from cleaned

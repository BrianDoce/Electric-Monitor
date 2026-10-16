with source as (

    select * from {{ source('raw', 'raw_eia_demand') }}

),

cleaned as (

    select
        -- EIA periods are UTC. Keep the UTC hour as the unambiguous key and
        -- derive Pacific local time for display and daily grouping.
        strptime(period, '%Y-%m-%dT%H') as period_hour_utc,
        timezone('America/Los_Angeles', strptime(period, '%Y-%m-%dT%H') at time zone 'UTC') as period_hour,
        respondent,
        respondent_name,
        cast(demand_mwh as double) as demand_mwh,
        loaded_at

    from source
    where demand_mwh is not null

)

select * from cleaned

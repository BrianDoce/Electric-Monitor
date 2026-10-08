with source as (

    select * from {{ source('raw', 'raw_eia_demand') }}

),

cleaned as (

    select
        strptime(period, '%Y-%m-%dT%H') as period_hour,
        respondent,
        respondent_name,
        cast(demand_mwh as double) as demand_mwh,
        loaded_at

    from source
    where demand_mwh is not null

)

select * from cleaned

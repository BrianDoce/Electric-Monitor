-- Every hour between the first and last should be present exactly once.
with bounds as (
    select min(period_hour_utc) as lo, max(period_hour_utc) as hi
    from {{ ref('stg_eia_demand') }}
)
select count(*) as actual_hours,
       date_diff('hour', lo, hi) + 1 as expected_hours
from {{ ref('stg_eia_demand') }}, bounds
group by lo, hi
having count(*) != date_diff('hour', lo, hi) + 1

-- EIA publishes with a lag of a day or so. Fail if the newest hour is
-- more than 72 hours old, which means the source stopped updating.
select max(period_hour_utc) as latest_hour
from {{ ref('stg_eia_demand') }}
having max(period_hour_utc) < current_timestamp::timestamp - interval 72 hour

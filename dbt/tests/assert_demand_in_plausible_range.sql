-- CAISO hourly demand should sit well inside this band; values outside
-- usually mean a units or parsing problem upstream.
select period_hour_utc, demand_mwh
from {{ ref('stg_eia_demand') }}
where demand_mwh < 10000 or demand_mwh > 70000

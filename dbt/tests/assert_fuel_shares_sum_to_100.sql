-- Per-day fuel shares are rounded to 2 decimals across ~9 fuels.
select date, sum(pct_of_daily_generation) as total_pct
from {{ ref('mart_fuel_mix_daily') }}
group by date
having abs(sum(pct_of_daily_generation) - 100) > 0.5

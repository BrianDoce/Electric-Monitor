select date, renewable_pct
from {{ ref('mart_grid_daily_summary') }}
where renewable_pct < 0 or renewable_pct > 100

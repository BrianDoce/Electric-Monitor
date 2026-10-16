select period_hour_utc, temperature_f
from {{ ref('stg_weather') }}
where temperature_f < -10 or temperature_f > 130

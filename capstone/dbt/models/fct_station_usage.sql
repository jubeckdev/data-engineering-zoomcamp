select station_code, observed_year, avg_daily_movements,
       avg_weekday_movements, avg_non_workday_movements
from {{ ref('stg_station_usage') }}

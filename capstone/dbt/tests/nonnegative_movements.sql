select * from {{ ref('fct_station_usage') }}
where avg_daily_movements < 0 or avg_weekday_movements < 0 or avg_non_workday_movements < 0

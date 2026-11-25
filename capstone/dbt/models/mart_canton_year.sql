select f.observed_year, s.canton, count(*) as station_count,
       count(f.avg_daily_movements) as measured_station_count,
       sum(f.avg_daily_movements) as avg_daily_movements,
       sum(f.avg_weekday_movements) as avg_weekday_movements,
       sum(f.avg_non_workday_movements) as avg_non_workday_movements
from {{ ref('fct_station_usage') }} f
join {{ ref('mart_station_year') }} s
  on f.station_code=s.station_code and f.observed_year=s.observed_year
group by f.observed_year, s.canton

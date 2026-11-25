with eligible as (
    select station_code from {{ ref('fct_station_usage') }}
    group by station_code
    having count(distinct observed_year) =
      (select count(distinct observed_year) from {{ ref('fct_station_usage') }})
    and count(avg_daily_movements) = count(*)
)
select observed_year, count(*) as station_count,
       sum(avg_daily_movements) as avg_daily_movements
from {{ ref('fct_station_usage') }}
join eligible using (station_code)
group by observed_year

select station_code, observed_year
from {{ ref('fct_station_usage') }}
group by 1,2 having count(*) != 1

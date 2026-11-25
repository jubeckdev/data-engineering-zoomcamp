select station_code, uic, station_name, canton, infrastructure_operator,
       latitude, longitude, observed_year as latest_observed_year
from {{ ref('stg_station_usage') }}
qualify row_number() over (partition by station_code order by observed_year desc) = 1

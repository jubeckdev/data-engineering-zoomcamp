select 1 from {{ ref('mart_common_cohort_year') }}
having min(station_count) != max(station_count) or min(station_count) = 0

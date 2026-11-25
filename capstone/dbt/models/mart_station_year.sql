-- Keep names, operator coverage and canton as reported in that year.
select * from {{ ref('stg_station_usage') }}

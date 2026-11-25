select 1
where (select count(*) from {{ ref('fct_station_usage') }})
    != (select count(*) from {{ source('raw', 'station_usage') }})

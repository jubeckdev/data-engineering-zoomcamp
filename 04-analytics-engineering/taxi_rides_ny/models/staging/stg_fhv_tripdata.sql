{{ config(materialized='view') }}
select
    dispatching_base_num,
    cast(pickup_datetime as timestamp) as pickup_datetime,
    cast(dropoff_datetime as timestamp) as dropoff_datetime,
    cast(pulocationid as integer) as pickup_location_id,
    cast(dolocationid as integer) as dropoff_location_id,
    cast(sr_flag as integer) as shared_ride_flag,
    affiliated_base_number
from {{ source('raw', 'fhv_tripdata') }}
where dispatching_base_num is not null
{% if target.name == 'dev' %}
  and cast(pickup_datetime as timestamp) >= '2019-01-01'
  and cast(pickup_datetime as timestamp) < '2019-02-01'
{% endif %}

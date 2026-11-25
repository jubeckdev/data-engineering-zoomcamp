with fact as (
    select observed_year, count(*) as n from {{ ref('fct_station_usage') }} group by 1
), report as (
    select observed_year, sum(station_count) as n from {{ ref('mart_canton_year') }} group by 1
)
select * from fact full outer join report using (observed_year)
where fact.n is null or report.n is null or fact.n != report.n

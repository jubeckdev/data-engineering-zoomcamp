select
    cast(code_codice as varchar) as station_code,
    cast(uic as bigint) as uic,
    cast(jahr_annee_anno as integer) as observed_year,
    bahnhof_gare_stazione as station_name,
    kt_ct_cantone as canton,
    isb_gi as infrastructure_operator,
    evu_ef_itf as included_rail_operators,
    cast(dtv_tjm_tgm as decimal(18,2)) as avg_daily_movements,
    cast(dwv_tmjo_tfm as decimal(18,2)) as avg_weekday_movements,
    cast(dnwv_tmjno_tmgnl as decimal(18,2)) as avg_non_workday_movements,
    remarks as coverage_note,
    cast(geopos.lat as double) as latitude,
    cast(geopos.lon as double) as longitude
from {{ source('raw', 'station_usage') }}

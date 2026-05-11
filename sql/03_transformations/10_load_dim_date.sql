-- Genera dim_date cubriendo el rango completo de ventas y devoluciones.
truncate table dwh.dim_date cascade;

with bounds as (
    select  least(
                (select min(sale_date)::date   from staging.sale),
                (select min(return_date)::date from staging.return_item)
            ) as ts,
            greatest(
                (select max(sale_date)::date   from staging.sale),
                (select max(return_date)::date from staging.return_item)
            ) as te
),
calendar as (
    select generate_series(b.ts, b.te, interval '1 day')::date as d from bounds b
)
insert into dwh.dim_date
select  to_char(d, 'YYYYMMDD')::int                        as date_id,
        d                                                   as full_date,
        extract(year  from d)::int                          as year,
        extract(quarter from d)::int                        as quarter,
        extract(month from d)::int                          as month,
        to_char(d, 'TMMonth')                               as month_name,
        extract(day from d)::int                            as day,
        extract(isodow from d)::int                         as day_of_week,
        to_char(d, 'TMDay')                                 as day_name,
        extract(week from d)::int                           as week_of_year,
        extract(isodow from d) in (6,7)                     as is_weekend
from calendar;

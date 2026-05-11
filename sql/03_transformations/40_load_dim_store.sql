truncate table dwh.dim_store restart identity cascade;

insert into dwh.dim_store
       (store_id, name, address, city, postal_code,
        district, area_type, zone_orientation, opened_date)
select  s.store_id,
        s.name,
        s.address,
        coalesce(s.city, z.city)        as city,
        s.postal_code,
        z.district,
        z.area_type,
        z.zone_orientation,
        s.opened_date
from staging.store s
left join staging.city_zone z on z.postal_code = s.postal_code;

-- dim_product: combina staging.product (50) con staging.central_product (49).
-- Usa central_product cuando exista (tiene unit_cost y FKs a brand/category);
-- cuando falta (1 producto), cae al texto plano de staging.product.

truncate table dwh.dim_product restart identity cascade;

insert into dwh.dim_product (product_id, name, category, brand, sku, unit_cost, unit_price)
select  p.product_id,
        coalesce(cp.name, p.name)                                         as name,
        coalesce(cat.name, p.category)                                    as category,
        coalesce(b.name,  p.manufacturer)                                 as brand,
        cp.sku,
        cp.unit_cost,
        coalesce(cp.unit_price, p.price)                                  as unit_price
from staging.product p
left join staging.central_product cp on cp.product_id = p.product_id
left join staging.category   cat on cat.category_id = cp.category_id
left join staging.brand      b   on b.brand_id      = cp.brand_id;

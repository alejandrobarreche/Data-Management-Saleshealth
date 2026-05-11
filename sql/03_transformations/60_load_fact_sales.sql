truncate table dwh.fact_sales cascade;

insert into dwh.fact_sales
       (sale_item_id, sale_id, sale_date_id, customer_sk, product_sk,
        store_sk, offer_sk, quantity, unit_price, unit_cost,
        subtotal, cost, margin)
select  si.sale_item_id,
        s.sale_id,
        to_char(s.sale_date, 'YYYYMMDD')::int          as sale_date_id,
        dc.customer_sk,
        dp.product_sk,
        ds.store_sk,
        do2.offer_sk,
        si.quantity,
        si.unit_price,
        dp.unit_cost,
        si.subtotal,
        coalesce(dp.unit_cost, 0) * si.quantity        as cost,
        si.subtotal - coalesce(dp.unit_cost, 0) * si.quantity as margin
from staging.sale_item si
join staging.sale       s  on s.sale_id    = si.sale_id
left join dwh.dim_customer dc on dc.customer_id = s.customer_id
left join dwh.dim_product  dp on dp.product_id  = si.product_id
left join dwh.dim_store    ds on ds.store_id    = s.store_id
left join dwh.dim_offer    do2 on do2.offer_id  = si.offer_id;

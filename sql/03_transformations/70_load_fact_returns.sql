truncate table dwh.fact_returns cascade;

insert into dwh.fact_returns
       (return_id, sale_item_id, return_date_id, customer_sk, product_sk,
        store_sk, reason_sk, quantity, returned_value)
select  ri.return_id,
        ri.sale_item_id,
        to_char(ri.return_date, 'YYYYMMDD')::int  as return_date_id,
        fs.customer_sk,
        fs.product_sk,
        fs.store_sk,
        drr.reason_sk,
        ri.quantity,
        ri.quantity * fs.unit_price               as returned_value
from staging.return_item ri
left join dwh.fact_sales       fs  on fs.sale_item_id = ri.sale_item_id
left join dwh.dim_return_reason drr on drr.reason_id  = ri.reason_id;

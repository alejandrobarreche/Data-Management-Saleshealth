-- Tablas de hechos.

drop table if exists dwh.fact_sales cascade;
create table dwh.fact_sales (
    sale_item_id  int           primary key,
    sale_id       int           not null,
    sale_date_id  int           not null references dwh.dim_date(date_id),
    customer_sk   int           references dwh.dim_customer(customer_sk),
    product_sk    int           references dwh.dim_product(product_sk),
    store_sk      int           references dwh.dim_store(store_sk),
    offer_sk      int           references dwh.dim_offer(offer_sk),
    quantity      int           not null,
    unit_price    numeric(12,2) not null,
    unit_cost     numeric(12,2),
    subtotal      numeric(14,2) not null,
    cost          numeric(14,2),
    margin        numeric(14,2)
);

create index ix_fs_customer on dwh.fact_sales(customer_sk);
create index ix_fs_product  on dwh.fact_sales(product_sk);
create index ix_fs_store    on dwh.fact_sales(store_sk);
create index ix_fs_date     on dwh.fact_sales(sale_date_id);

drop table if exists dwh.fact_returns cascade;
create table dwh.fact_returns (
    return_id        int           primary key,
    sale_item_id     int           references dwh.fact_sales(sale_item_id),
    return_date_id   int           not null references dwh.dim_date(date_id),
    customer_sk      int           references dwh.dim_customer(customer_sk),
    product_sk       int           references dwh.dim_product(product_sk),
    store_sk         int           references dwh.dim_store(store_sk),
    reason_sk        int           references dwh.dim_return_reason(reason_sk),
    quantity         int           not null,
    returned_value   numeric(14,2)
);

create index ix_fr_customer on dwh.fact_returns(customer_sk);
create index ix_fr_product  on dwh.fact_returns(product_sk);
create index ix_fr_date     on dwh.fact_returns(return_date_id);

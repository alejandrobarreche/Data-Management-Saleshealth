-- Tablas de dimensión.

drop table if exists dwh.dim_date cascade;
create table dwh.dim_date (
    date_id      int           primary key,         -- yyyymmdd
    full_date    date          not null unique,
    year         smallint      not null,
    quarter      smallint      not null,
    month        smallint      not null,
    month_name   varchar(15)   not null,
    day          smallint      not null,
    day_of_week  smallint      not null,
    day_name     varchar(15)   not null,
    week_of_year smallint      not null,
    is_weekend   boolean       not null
);

drop table if exists dwh.dim_customer cascade;
create table dwh.dim_customer (
    customer_sk  serial        primary key,
    customer_id  int           not null unique,
    full_name    varchar(200),
    email        varchar(200),
    phone        varchar(50),
    signup_date  date
);

drop table if exists dwh.dim_product cascade;
create table dwh.dim_product (
    product_sk   serial        primary key,
    product_id   int           not null unique,
    name         varchar(200),
    category     varchar(100),
    brand        varchar(100),
    sku          varchar(50),
    unit_cost    numeric(12,2),
    unit_price   numeric(12,2)
);

drop table if exists dwh.dim_store cascade;
create table dwh.dim_store (
    store_sk     serial        primary key,
    store_id     int           not null unique,
    name         varchar(200),
    address      varchar(200),
    city         varchar(100),
    postal_code  varchar(10),
    district     varchar(100),
    area_type    varchar(50),
    zone_orientation varchar(50),
    opened_date  date
);

drop table if exists dwh.dim_offer cascade;
create table dwh.dim_offer (
    offer_sk         serial      primary key,
    offer_id         int         not null unique,
    name             varchar(200),
    discount_percent numeric(5,2),
    start_date       date,
    end_date         date
);

drop table if exists dwh.dim_return_reason cascade;
create table dwh.dim_return_reason (
    reason_sk    serial        primary key,
    reason_id    int           not null unique,
    reason       text,
    active       boolean
);

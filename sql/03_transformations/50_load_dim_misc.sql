truncate table dwh.dim_offer         restart identity cascade;
truncate table dwh.dim_return_reason  restart identity cascade;

insert into dwh.dim_offer (offer_id, name, discount_percent, start_date, end_date)
select offer_id, name, discount_percent, start_date, end_date from staging.offer;

insert into dwh.dim_return_reason (reason_id, reason, active)
select reason_id, reason, active from staging.return_reason;

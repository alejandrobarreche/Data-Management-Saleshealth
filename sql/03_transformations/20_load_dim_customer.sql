truncate table dwh.dim_customer restart identity cascade;

insert into dwh.dim_customer (customer_id, full_name, email, phone, signup_date)
select  customer_id,
        trim(both ' ' from
            coalesce(first_name,'') || ' ' ||
            coalesce(last_name,'')  || ' ' ||
            coalesce(last_name2,'')) as full_name,
        email,
        phone,
        signup_date
from staging.customer;

select
    id                              as customer_id,
    first_name,
    last_name,
    first_name || ' ' || last_name  as full_name,
    country,
    segment,
    cast(signup_date as date)       as signup_date
from {{ ref('raw_customers') }}

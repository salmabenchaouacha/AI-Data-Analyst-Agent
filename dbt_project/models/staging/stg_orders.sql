select
    id                                                    as order_id,
    customer_id,
    cast(order_date as date)                              as order_date,
    substr(cast(order_date as varchar), 1, 7)             as order_month,
    cast(substr(cast(order_date as varchar), 1, 4) as integer) as order_year,
    status
from {{ ref('raw_orders') }}

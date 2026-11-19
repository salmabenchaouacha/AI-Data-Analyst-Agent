select
    id                                                       as order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    discount_rate,
    round(quantity * unit_price, 2)                          as gross_amount,
    round(quantity * unit_price * (1 - discount_rate), 2)    as net_amount
from {{ ref('raw_order_items') }}

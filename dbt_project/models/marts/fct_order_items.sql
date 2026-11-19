select
    i.order_item_id,
    i.order_id,
    o.customer_id,
    o.order_date,
    o.order_month,
    o.order_year,
    o.status,
    i.product_id,
    p.product_name,
    p.category,
    i.quantity,
    i.unit_price,
    i.discount_rate,
    i.gross_amount,
    i.net_amount,
    round(i.quantity * p.unit_cost, 2)                  as cost_amount,
    round(i.net_amount - i.quantity * p.unit_cost, 2)   as margin_amount
from {{ ref('stg_order_items') }} i
join {{ ref('stg_orders') }}   o on i.order_id = o.order_id
join {{ ref('stg_products') }} p on i.product_id = p.product_id

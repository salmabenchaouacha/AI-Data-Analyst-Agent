with items as (
    select
        order_id,
        count(*)            as n_items,
        sum(quantity)       as total_quantity,
        sum(gross_amount)   as gross_amount,
        sum(net_amount)     as net_amount
    from {{ ref('stg_order_items') }}
    group by order_id
),
pay as (
    select
        order_id,
        min(payment_method) as payment_method,
        sum(amount)         as amount_paid
    from {{ ref('stg_payments') }}
    group by order_id
)
select
    o.order_id,
    o.customer_id,
    o.order_date,
    o.order_month,
    o.order_year,
    o.status,
    case when o.status = 'completed' then 1 else 0 end  as is_completed,
    items.n_items,
    items.total_quantity,
    round(items.gross_amount, 2)                         as gross_amount,
    round(items.net_amount, 2)                           as net_amount,
    pay.payment_method,
    round(coalesce(pay.amount_paid, 0), 2)               as amount_paid
from {{ ref('stg_orders') }} o
join items    on o.order_id = items.order_id
left join pay on o.order_id = pay.order_id

with orders as (
    select
        customer_id,
        min(order_date)                                              as first_order_date,
        max(order_date)                                              as last_order_date,
        count(*)                                                     as n_orders,
        sum(is_completed)                                            as n_completed_orders,
        sum(case when is_completed = 1 then net_amount else 0 end)  as lifetime_revenue
    from {{ ref('fct_orders') }}
    group by customer_id
)
select
    c.customer_id,
    c.full_name,
    c.country,
    c.segment,
    c.signup_date,
    o.first_order_date,
    o.last_order_date,
    coalesce(o.n_orders, 0)                                  as n_orders,
    coalesce(o.n_completed_orders, 0)                        as n_completed_orders,
    round(coalesce(o.lifetime_revenue, 0), 2)                as lifetime_revenue,
    case when coalesce(o.n_completed_orders, 0) >= 2 then 1 else 0 end as is_repeat_customer
from {{ ref('stg_customers') }} c
left join orders o on c.customer_id = o.customer_id

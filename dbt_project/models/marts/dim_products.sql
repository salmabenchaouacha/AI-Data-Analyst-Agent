with sales as (
    select
        product_id,
        sum(quantity)       as units_sold,
        sum(net_amount)     as revenue,
        sum(margin_amount)  as margin
    from {{ ref('fct_order_items') }}
    where status = 'completed'
    group by product_id
)
select
    p.product_id,
    p.product_name,
    p.category,
    p.unit_price,
    p.unit_cost,
    coalesce(s.units_sold, 0)           as units_sold,
    round(coalesce(s.revenue, 0), 2)    as revenue,
    round(coalesce(s.margin, 0), 2)     as margin
from {{ ref('stg_products') }} p
left join sales s on p.product_id = s.product_id

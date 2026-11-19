select
    id          as product_id,
    name        as product_name,
    category,
    unit_price,
    unit_cost
from {{ ref('raw_products') }}

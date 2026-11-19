{% docs staging_note %}
Staging models rename raw columns and cast types. The agent should query the marts
(fct_orders, fct_order_items, dim_customers, dim_products), not the staging views.
{% enddocs %}

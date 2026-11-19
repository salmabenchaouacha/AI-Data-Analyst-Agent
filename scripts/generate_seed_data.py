"""Generate deterministic e-commerce seed data for the dbt project.

Usage: python scripts/generate_seed_data.py
Writes CSVs to dbt_project/seeds/ (raw_customers, raw_products, raw_orders,
raw_order_items, raw_payments). Same seed -> same data -> reproducible eval.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(__file__).resolve().parents[1] / "dbt_project" / "seeds"
OUT.mkdir(parents=True, exist_ok=True)

COUNTRIES = ["France", "Germany", "Spain", "Italy", "Belgium", "Tunisia"]
SEGMENTS = ["consumer", "business"]
CATEGORIES = {
    "Electronics": [("Wireless Mouse", 25), ("Mechanical Keyboard", 89), ("USB-C Hub", 45),
                    ("27in Monitor", 279), ("Noise-Cancelling Headphones", 199)],
    "Home": [("Desk Lamp", 39), ("Office Chair", 249), ("Standing Desk", 499), ("Plant Pot", 15)],
    "Books": [("Data Engineering Handbook", 49), ("SQL Cookbook", 35), ("ML Systems Design", 55)],
    "Sports": [("Yoga Mat", 29), ("Running Shoes", 119), ("Water Bottle", 19)],
}
STATUSES = ["completed"] * 8 + ["returned", "cancelled"]
PAYMENT_METHODS = ["credit_card", "paypal", "bank_transfer", "gift_card"]
FIRST = ["Lina", "Omar", "Sara", "Yassine", "Emma", "Lucas", "Mia", "Noah", "Ines", "Adam",
         "Lea", "Hugo", "Nour", "Amir", "Chloe", "Louis", "Rania", "Karim", "Julie", "Paul"]
LAST = ["Martin", "Bernard", "Trabelsi", "Garcia", "Rossi", "Muller", "Dubois", "Ben Ali",
        "Lopez", "Peeters", "Moreau", "Fischer"]


def write(name, header, rows):
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# products
products, pid = [], 1
for cat, items in CATEGORIES.items():
    for pname, price in items:
        cost = round(price * random.uniform(0.45, 0.7), 2)
        products.append((pid, pname, cat, price, cost))
        pid += 1
write("raw_products", ["id", "name", "category", "unit_price", "unit_cost"], products)

# customers
customers = []
start = date(2024, 1, 1)
for cid in range(1, 201):
    signup = start + timedelta(days=random.randint(0, 600))
    customers.append((cid, random.choice(FIRST), random.choice(LAST), random.choice(COUNTRIES),
                      random.choices(SEGMENTS, weights=[3, 1])[0], signup.isoformat()))
write("raw_customers", ["id", "first_name", "last_name", "country", "segment", "signup_date"], customers)

# orders, items, payments
orders, items, payments = [], [], []
oid = iid = payid = 1
end = date(2025, 12, 31)
for c in customers:
    cid, signup = c[0], date.fromisoformat(c[5])
    for _ in range(random.choices([0, 1, 2, 3, 4, 6, 9], weights=[2, 4, 4, 3, 2, 1, 1])[0]):
        span = (end - signup).days
        if span <= 0:
            continue
        odate = signup + timedelta(days=random.randint(0, span))
        status = random.choice(STATUSES)
        orders.append((oid, cid, odate.isoformat(), status))
        total = 0.0
        for p in random.sample(products, random.randint(1, 4)):
            qty = random.choices([1, 2, 3], weights=[6, 3, 1])[0]
            discount = random.choice([0, 0, 0, 0.1, 0.2])
            items.append((iid, oid, p[0], qty, p[3], discount))
            total += qty * p[3] * (1 - discount)
            iid += 1
        if status != "cancelled":
            payments.append((payid, oid, random.choice(PAYMENT_METHODS), round(total, 2)))
            payid += 1
        oid += 1
write("raw_orders", ["id", "customer_id", "order_date", "status"], orders)
write("raw_order_items", ["id", "order_id", "product_id", "quantity", "unit_price", "discount_rate"], items)
write("raw_payments", ["id", "order_id", "payment_method", "amount"], payments)

print(f"customers={len(customers)} products={len(products)} orders={len(orders)} "
      f"items={len(items)} payments={len(payments)} -> {OUT}")

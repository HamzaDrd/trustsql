"""
Generate MESSY raw data, like you would receive from real source systems.

This simulates the "source" side of a pipeline. In a real job, these files
would come from an API, an export from another team, or a CRM.
Run once:  python scripts/generate_raw.py

The mess is on purpose, so the pipeline has something to clean:
- duplicate customers, emails with spaces and capitals, missing emails
- dates in different formats
- prices stored as text like "€19.99"
- orders pointing to customers that don't exist
- negative quantities
"""
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
SEED = 42  # same seed = same data every time (reproducible)

fake = Faker()
Faker.seed(SEED)
random.seed(SEED)


def messy_date(d: date) -> str:
    """Return a date in one of several formats, like real exports do."""
    fmt = random.choice(["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"])
    return d.strftime(fmt)


def generate_customers(n=200):
    rows = []
    for i in range(1, n + 1):
        email = fake.unique.email()
        if random.random() < 0.15:
            email = "  " + email.upper() + " "  # messy formatting
        if random.random() < 0.05:
            email = ""  # missing email
        rows.append({
            "customer_id": i,
            "name": fake.name(),
            "email": email,
            "country": random.choice(["Belgium", "belgium", "Netherlands", "France", "Germany", "BE"]),
            "city": fake.city(),
            "signup_date": messy_date(fake.date_between("-3y", "-2y")),
        })
    # exact duplicates (the same customer exported twice)
    rows += random.sample(rows, 8)
    return rows


def generate_products(n=30):
    categories = ["Electronics", "Books", "Home", "Sports", "Toys"]
    rows = []
    for i in range(1, n + 1):
        price = round(random.uniform(5, 500), 2)
        rows.append({
            "product_id": i,
            "name": fake.unique.word().capitalize() + " " + random.choice(["Pro", "Lite", "Max", "Mini"]),
            "category": random.choice(categories),
            "price": f"€{price}" if random.random() < 0.3 else str(price),  # price as text
            "cost": round(price * random.uniform(0.4, 0.8), 2),
        })
    return rows


def generate_orders(n=2000, n_customers=200, n_products=30):
    orders, items = [], []
    item_id = 1
    start = date.today() - timedelta(days=730)
    for i in range(1, n + 1):
        customer_id = random.randint(1, n_customers)
        if random.random() < 0.01:
            customer_id = 9999  # orphan: customer does not exist
        orders.append({
            "order_id": i,
            "customer_id": customer_id,
            "order_date": messy_date(start + timedelta(days=random.randint(0, 729))),
            "status": random.choices(
                ["completed", "Completed", "cancelled", "refunded"], [80, 8, 8, 4]
            )[0],
        })
        for _ in range(random.randint(1, 4)):
            qty = random.randint(1, 5)
            if random.random() < 0.005:
                qty = -qty  # invalid value
            items.append({
                "order_item_id": item_id,
                "order_id": i,
                "product_id": random.randint(1, n_products),
                "quantity": qty,
                "unit_price": round(random.uniform(5, 500), 2),
            })
            item_id += 1
    return orders, items


def generate_employees(n=15):
    return [{
        "employee_id": i,
        "name": fake.name(),
        "department": random.choice(["Sales", "Marketing", "IT", "Finance", "HR"]),
        "salary": random.randint(32000, 95000),
        "hire_date": fake.date_between("-8y", "-1m").isoformat(),
    } for i in range(1, n + 1)]


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    orders, items = generate_orders()
    write_csv(RAW_DIR / "customers.csv", generate_customers())
    write_csv(RAW_DIR / "products.csv", generate_products())
    write_csv(RAW_DIR / "order_items.csv", items)
    write_csv(RAW_DIR / "employees.csv", generate_employees())
    # orders come as JSON, to practice reading a second file format
    (RAW_DIR / "orders.json").write_text(json.dumps(orders, indent=2), encoding="utf-8")
    print(f"Raw files written to {RAW_DIR}")


if __name__ == "__main__":
    main()

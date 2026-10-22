"""
DATA QUALITY CHECKS: run on the clean data BEFORE loading.

If a check fails, the pipeline stops and the old database stays untouched.
Better no new data than wrong data.
"""
import pandas as pd

from pipelines.config import MAX_REJECT_RATE, MIN_ROWS
from pipelines.logger import get_logger

log = get_logger()

PRIMARY_KEYS = {
    "customers": "customer_id",
    "products": "product_id",
    "orders": "order_id",
    "order_items": "order_item_id",
    "employees": "employee_id",
}
REQUIRED_COLUMNS = {
    "customers": ["name", "signup_date"],
    "products": ["name", "price"],
    "orders": ["customer_id", "order_date", "status"],
    "order_items": ["order_id", "product_id", "quantity", "unit_price"],
    "employees": ["name", "salary"],
}


class DataQualityError(Exception):
    pass


def check_table(table: str, clean: pd.DataFrame, raw_count: int) -> list[str]:
    """Return a list of failure messages (empty list = all good)."""
    failures = []
    pk = PRIMARY_KEYS[table]

    # 1. Row count
    if len(clean) < MIN_ROWS[table]:
        failures.append(f"{table}: only {len(clean)} rows, expected at least {MIN_ROWS[table]}")

    # 2. Reject rate
    reject_rate = 1 - len(clean) / raw_count if raw_count else 1
    if reject_rate > MAX_REJECT_RATE:
        failures.append(f"{table}: {reject_rate:.1%} of rows rejected (max {MAX_REJECT_RATE:.0%})")

    # 3. Duplicates in the primary key
    dupes = clean[pk].duplicated().sum()
    if dupes:
        failures.append(f"{table}: {dupes} duplicate values in {pk}")

    # 4. Missing values in required columns
    for col in REQUIRED_COLUMNS[table]:
        missing = clean[col].isna().sum()
        if missing:
            failures.append(f"{table}: {missing} missing values in {col}")

    log.info(f"QUALITY  {table:<12} {'PASS' if not failures else 'FAIL'} "
             f"(reject rate {reject_rate:.1%})")
    return failures


def check_relationships(clean: dict[str, pd.DataFrame]) -> list[str]:
    """Every foreign key must point to an existing row."""
    failures = []
    checks = [
        ("orders", "customer_id", "customers"),
        ("order_items", "order_id", "orders"),
        ("order_items", "product_id", "products"),
    ]
    for child, col, parent in checks:
        orphans = (~clean[child][col].isin(clean[parent][col])).sum()
        if orphans:
            failures.append(f"{child}.{col}: {orphans} rows point to a missing {parent}")
    return failures


def run_quality_checks(clean: dict[str, pd.DataFrame], raw_counts: dict[str, int]):
    failures = []
    for table, df in clean.items():
        failures += check_table(table, df, raw_counts[table])
    failures += check_relationships(clean)

    if failures:
        for f in failures:
            log.error(f"QUALITY  {f}")
        raise DataQualityError(f"{len(failures)} data quality check(s) failed")
    log.info("QUALITY  all checks passed")

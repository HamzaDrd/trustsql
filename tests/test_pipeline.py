"""
Tests for the pipeline. Run with:  pytest

Two kinds of tests:
- Unit tests: feed a tiny hand-made DataFrame to one transform function
  and check that the bad rows are rejected for the right reason.
- End-to-end tests: run the full pipeline and check the result,
  including idempotency (running twice gives the same database).
"""
import hashlib
import sqlite3

import pandas as pd
import pytest

from pipelines import transform
from pipelines.config import DB_PATH, RAW_DIR
from pipelines.run_pipeline import main


# ---------- unit tests ----------

def test_parse_dates_handles_all_formats():
    s = pd.Series(["2025-03-01", "01/03/2025", "2025/03/01", "not a date"])
    result = transform.parse_dates(s)
    assert list(result[:3].astype(str)) == ["2025-03-01"] * 3
    assert pd.isna(result[3])


def test_to_number_strips_euro_sign():
    assert list(transform.to_number(pd.Series(["€19.99", "5", "abc"])).fillna(-1)) == [19.99, 5.0, -1]


def test_customers_cleaning():
    raw = pd.DataFrame({
        "customer_id": ["1", "2", "2", "3"],
        "name": ["Ann", "Bob", "Bob", ""],
        "email": ["  ANN@X.COM ", "bob@x.com", "bob@x.com", "c@x.com"],
        "country": ["be", "Belgium", "Belgium", "France"],
        "signup_date": ["2024-01-01", "01/02/2024", "01/02/2024", "2024-01-01"],
    })
    clean, rejected = transform.transform_customers(raw)

    assert list(clean["customer_id"]) == [1, 2]
    assert clean.loc[0, "email"] == "ann@x.com"       # trimmed + lowercase
    assert clean.loc[0, "country"] == "Belgium"        # "be" standardised
    assert set(rejected["reject_reason"]) == {"exact duplicate row", "missing name"}


def test_orders_reject_unknown_customer_and_bad_status():
    raw = pd.DataFrame({
        "order_id": ["1", "2", "3"],
        "customer_id": ["1", "999", "1"],
        "order_date": ["2025-01-01"] * 3,
        "status": ["Completed", "completed", "lost"],
    })
    clean, rejected = transform.transform_orders(raw, valid_customer_ids={1})
    assert list(clean["order_id"]) == [1]
    assert clean.loc[0, "status"] == "completed"
    assert set(rejected["reject_reason"]) == {"unknown customer_id", "invalid status"}


def test_order_items_reject_negative_quantity():
    raw = pd.DataFrame({
        "order_item_id": ["1", "2"], "order_id": ["1", "1"], "product_id": ["1", "1"],
        "quantity": ["2", "-1"], "unit_price": ["10", "10"],
    })
    clean, rejected = transform.transform_order_items(raw, {1}, {1})
    assert len(clean) == 1
    assert rejected.iloc[0]["reject_reason"] == "quantity not positive"


# ---------- end-to-end tests ----------

def db_fingerprint() -> str:
    """Hash of all table contents, to compare two runs."""
    conn = sqlite3.connect(DB_PATH)
    h = hashlib.sha256()
    for table in ["customers", "products", "orders", "order_items", "employees"]:
        for row in conn.execute(f"SELECT * FROM {table} ORDER BY 1"):
            h.update(repr(row).encode())
    conn.close()
    return h.hexdigest()


@pytest.fixture(scope="module")
def pipeline_ran():
    if not (RAW_DIR / "customers.csv").exists():
        pytest.skip("No raw data. Run: python scripts/generate_raw.py")
    assert main() == 0


def test_pipeline_is_idempotent(pipeline_ran):
    first = db_fingerprint()
    assert main() == 0
    assert db_fingerprint() == first


def test_raw_files_are_not_modified(pipeline_ran):
    before = {p.name: p.read_bytes() for p in RAW_DIR.iterdir()}
    assert main() == 0
    after = {p.name: p.read_bytes() for p in RAW_DIR.iterdir()}
    assert before == after


def test_loaded_data_has_no_orphans(pipeline_ran):
    conn = sqlite3.connect(DB_PATH)
    orphans = conn.execute("""
        SELECT COUNT(*) FROM orders o
        LEFT JOIN customers c ON c.customer_id = o.customer_id
        WHERE c.customer_id IS NULL
    """).fetchone()[0]
    conn.close()
    assert orphans == 0

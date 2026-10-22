"""
LOAD: write clean data into the SQLite database.

Idempotency and safety:
1. Build a brand-new database in a temporary file.
2. Create the tables from sql/schema.sql (with keys and constraints).
3. Insert the clean data.
4. Only if everything worked, swap the temp file in place of data/sales.db.

Running it twice gives exactly the same database (no duplicates), and if
anything fails halfway, the old database is never left half-written.
"""
import os
import sqlite3

import pandas as pd

from pipelines.config import DB_PATH, POST_LOAD_CHECKS_PATH, REJECTED_DIR, SCHEMA_PATH
from pipelines.logger import get_logger
from pipelines.quality import DataQualityError

log = get_logger()

LOAD_ORDER = ["customers", "products", "orders", "order_items", "employees"]  # parents first


def load_all(clean: dict[str, pd.DataFrame]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = DB_PATH.with_suffix(".tmp.db")
    if tmp_path.exists():
        tmp_path.unlink()

    conn = sqlite3.connect(tmp_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        for table in LOAD_ORDER:
            # if_exists="append" because schema.sql already created the table
            # with the right types and constraints.
            clean[table].to_sql(table, conn, if_exists="append", index=False)
            log.info(f"LOAD     {table:<12} {len(clean[table]):>6} rows")
        conn.commit()
        run_sql_checks(conn)  # still on the temp file: a failure keeps the old DB
    except Exception:
        conn.close()
        tmp_path.unlink(missing_ok=True)
        raise
    conn.close()

    os.replace(tmp_path, DB_PATH)  # atomic swap
    log.info(f"LOAD     database ready at {DB_PATH}")


def run_sql_checks(conn: sqlite3.Connection) -> None:
    """Run every query in sql/post_load_checks.sql; each must return 0."""
    failures = []
    blocks = POST_LOAD_CHECKS_PATH.read_text(encoding="utf-8").split("-- check:")[1:]
    for block in blocks:
        name, query = block.split("\n", 1)
        count = conn.execute(query).fetchone()[0]
        if count:
            failures.append(f"{name.strip()}: {count}")
            log.error(f"SQL CHECK {name.strip()}: {count} rows")
        else:
            log.info(f"SQL CHECK {name.strip()}: OK")
    if failures:
        raise DataQualityError(f"{len(failures)} post-load SQL check(s) failed")


def save_rejected(rejected: dict[str, pd.DataFrame]) -> None:
    """Write rejected rows to data/rejected/<table>.csv (overwritten each run)."""
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    for table, df in rejected.items():
        path = REJECTED_DIR / f"{table}.csv"
        if df.empty:
            path.unlink(missing_ok=True)
            continue
        df.to_csv(path, index=False)
        log.warning(f"REJECTED {table:<12} {len(df):>6} rows -> {path.name}")

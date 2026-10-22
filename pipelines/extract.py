"""
EXTRACT: read the raw files into pandas DataFrames.

Rules:
- Read only. Never modify files in data/raw/.
- Read everything as text (dtype=str). Converting types is the job of
  transform, where we can catch and log bad values instead of crashing here.
"""
import json

import pandas as pd

from pipelines.config import RAW_DIR
from pipelines.logger import get_logger

log = get_logger()

SOURCES = {
    "customers": "customers.csv",
    "products": "products.csv",
    "orders": "orders.json",
    "order_items": "order_items.csv",
    "employees": "employees.csv",
}


def read_source(filename: str) -> pd.DataFrame:
    path = RAW_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing raw file: {path}. Run scripts/generate_raw.py first.")
    if path.suffix == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    if path.suffix == ".json":
        return pd.DataFrame(json.loads(path.read_text(encoding="utf-8"))).astype(str)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def extract_all() -> dict[str, pd.DataFrame]:
    data = {}
    for table, filename in SOURCES.items():
        data[table] = read_source(filename)
        log.info(f"EXTRACT  {table:<12} {len(data[table]):>6} rows from {filename}")
    return data

"""All paths and settings in one place, so no other file hard-codes them."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = ROOT / "data" / "raw"            # input: never edited by the pipeline
REJECTED_DIR = ROOT / "data" / "rejected"  # bad rows go here, with a reason
DB_PATH = ROOT / "data" / "sales.db"       # output: what the app queries
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
POST_LOAD_CHECKS_PATH = ROOT / "sql" / "post_load_checks.sql"
LOG_DIR = ROOT / "logs"

# Data quality thresholds: if more than this share of a table is rejected,
# the run FAILS instead of loading a half-empty table.
MAX_REJECT_RATE = 0.10

# Expected minimum row counts after cleaning (catches empty/broken inputs).
MIN_ROWS = {
    "customers": 100,
    "products": 10,
    "orders": 1000,
    "order_items": 1000,
    "employees": 5,
}

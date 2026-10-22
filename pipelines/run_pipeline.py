"""
Run the whole pipeline:  python -m pipelines.run_pipeline

Steps: extract -> transform -> quality checks -> load
Each run gets an ID and is recorded in logs/run_history.csv.
Exit code 0 = success, 1 = failure (GitHub Actions and cron use this).
"""
import csv
import sys
import time
import uuid
from datetime import datetime

from pipelines.config import LOG_DIR
from pipelines.extract import extract_all
from pipelines.load import load_all, save_rejected
from pipelines.logger import get_logger
from pipelines.quality import run_quality_checks
from pipelines.transform import transform_all

log = get_logger()


def record_run(run_id, started, status, details):
    path = LOG_DIR / "run_history.csv"
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["run_id", "started_at", "finished_at", "status", "details"])
        writer.writerow([run_id, started, datetime.now().isoformat(timespec="seconds"), status, details])


def main() -> int:
    run_id = uuid.uuid4().hex[:8]
    started = datetime.now().isoformat(timespec="seconds")
    t0 = time.time()
    log.info(f"===== pipeline run {run_id} started =====")

    try:
        raw = extract_all()
        clean, rejected = transform_all(raw)
        save_rejected(rejected)
        run_quality_checks(clean, {t: len(df) for t, df in raw.items()})
        load_all(clean)
    except Exception as e:
        log.exception(f"===== pipeline run {run_id} FAILED: {e} =====")
        record_run(run_id, started, "failed", str(e))
        return 1

    summary = ", ".join(f"{t}={len(df)}" for t, df in clean.items())
    log.info(f"===== pipeline run {run_id} succeeded in {time.time() - t0:.1f}s =====")
    record_run(run_id, started, "success", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())


import sqlite3
import pandas as pd

# EXTRACT: read the raw file
df = pd.read_csv("data/raw/customers.csv")
print(f"Extracted {len(df)} rows")

# TRANSFORM: clean the data
df["email"] = df["email"].str.strip().str.lower()
df = df.drop_duplicates(subset="email")
df = df.dropna(subset=["name"])
print(f"{len(df)} rows after cleaning")

# LOAD: write to the database (replace = idempotent)
conn = sqlite3.connect("data/sales.db")
df.to_sql("customers", conn, if_exists="replace", index=False)
conn.close()
print("Loaded into data/sales.db")
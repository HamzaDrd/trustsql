# TrustSQL – ETL pipeline

A small but complete ETL pipeline that turns messy raw sales data into a clean
SQLite database. It is the data foundation of TrustSQL, the natural-language
SQL assistant.

```
data/raw/  ──►  EXTRACT  ──►  TRANSFORM  ──►  QUALITY CHECKS  ──►  LOAD  ──►  data/sales.db
 (messy)       read files    clean, type,     row counts, keys,    temp DB +
                             dedupe, reject   reject rate, FKs     SQL checks,
                                 │                                 atomic swap
                                 └──► data/rejected/*.csv (bad rows + reason)
```

## What each concept looks like in the code

| Concept | Where |
|---|---|
| **Extract** | `pipelines/extract.py` reads CSV and JSON, everything as text |
| **Transform** | `pipelines/transform.py` one function per table |
| **Load** | `pipelines/load.py` builds the DB from `sql/schema.sql` |
| **Raw data is never edited** | `data/raw/` is only read; a test checks the files are unchanged |
| **Idempotency** | Each run builds a fresh DB in a temp file and swaps it in; a test runs twice and compares |
| **Data quality checks** | `pipelines/quality.py` (Python) and `sql/post_load_checks.sql` (SQL) |
| **Bad data is caught, not hidden** | Rejected rows go to `data/rejected/<table>.csv` with a `reject_reason` |
| **Logging** | `logs/pipeline.log` (every step) and `logs/run_history.csv` (one row per run) |
| **Orchestration** | GitHub Actions (`.github/workflows/etl.yml`) and cron on your Mac |
| **Version control** | Everything except outputs is in Git (see `.gitignore`) |

## Project layout

```
trustsql/
├── .github/workflows/etl.yml   # runs the pipeline on GitHub
├── data/
│   ├── raw/                    # source data (committed, never edited)
│   ├── rejected/               # bad rows from the last run (not in Git)
│   └── sales.db                # output database (not in Git)
├── logs/                       # pipeline.log, run_history.csv (not in Git)
├── pipelines/
│   ├── config.py               # paths and thresholds
│   ├── logger.py               # logging setup
│   ├── extract.py
│   ├── transform.py
│   ├── quality.py
│   ├── load.py
│   └── run_pipeline.py         # entry point
├── scripts/
│   ├── generate_raw.py         # creates messy fake source data
│   └── run_pipeline.sh         # wrapper for cron
├── sql/
│   ├── schema.sql              # tables, keys, constraints
│   └── post_load_checks.sql    # SQL checks that must return 0
└── tests/test_pipeline.py
```

---

## Setup on a Mac (one time)

Open **Terminal** (Cmd + Space → "Terminal").

```bash
# 1. Check Python (need 3.11+). If missing: install from python.org
python3 --version

# 2. Go to the project folder (adjust the path to where you put it)
cd ~/trustsql

# 3. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # you'll see (venv) in front of your prompt

# 4. Install packages
pip install -r requirements.txt
```

Every time you open a new Terminal: `cd ~/trustsql && source venv/bin/activate`.

## Run it locally

```bash
python scripts/generate_raw.py      # only once: creates data/raw/
python -m pipelines.run_pipeline    # runs the full pipeline
pytest                              # runs the tests
```

Then look at the results:
- `logs/pipeline.log` – what happened, step by step
- `data/rejected/` – which rows were refused and why
- `data/sales.db` – open it in VS Code (SQLite Viewer extension) or [DB Browser for SQLite](https://sqlitebrowser.org)

**Try these to learn:**
1. Run the pipeline twice. Compare the row counts: identical (idempotent).
2. Simulate a broken source: in `data/raw/customers.csv`, delete the name from
   many rows and run again. The quality checks fail and `sales.db` stays
   untouched. Undo it with `git checkout data/raw/customers.csv` (after you've
   committed to Git) or `python scripts/generate_raw.py`.
3. Add a new rule in `transform.py` (e.g. reject employees hired in the future),
   then write a test for it.

---

## Put it on GitHub

```bash
git init
git add .
git commit -m "Add ETL pipeline"
```

Create an empty repository on github.com called `trustsql` (no README), then:

```bash
git remote add origin https://github.com/<your-username>/trustsql.git
git branch -M main
git push -u origin main
```

Open the repo → **Actions** tab. The pipeline runs on every push, daily at
06:00 UTC, and manually via **Run workflow**. The database, logs and rejected
rows are downloadable at the bottom of each run.

Status badge for this README:

```markdown
![ETL](https://github.com/<your-username>/trustsql/actions/workflows/etl.yml/badge.svg)
```

## Schedule it on your Mac (optional, cron)

```bash
chmod +x scripts/run_pipeline.sh
crontab -e
```

Add this line (runs every day at 07:00; use your real path from `pwd`):

```
0 7 * * * /Users/<you>/trustsql/scripts/run_pipeline.sh
```

Save and quit (in vim: `Esc`, then `:wq`, then Enter). Check with `crontab -l`.
It only runs while your Mac is awake. If nothing appears in `logs/cron.log`,
give **cron** Full Disk Access in System Settings → Privacy & Security.

---

## Next steps to grow it

- Incremental loads: only process new orders instead of rebuilding everything
- A second data source (a public API) in `extract.py`
- Orchestrate with **Prefect** or **Airflow** instead of cron
- Move the transform step to **dbt** (SQL models with built-in tests)
- Load into PostgreSQL instead of SQLite

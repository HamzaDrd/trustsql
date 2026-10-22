"""
TRANSFORM: turn messy raw data into clean, typed, consistent tables.

Every function returns two DataFrames:
- clean:    rows that are good enough to load
- rejected: rows we refused, with a "reject_reason" column

Bad rows are never silently dropped. They are kept (quarantined) so you can
see exactly what was removed and why.
"""
import pandas as pd

from pipelines.logger import get_logger

log = get_logger()

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]
COUNTRY_MAP = {"belgium": "Belgium", "be": "Belgium", "netherlands": "Netherlands",
               "france": "France", "germany": "Germany"}
VALID_STATUSES = {"completed", "cancelled", "refunded"}


# ---------- helpers ----------

def parse_dates(series: pd.Series) -> pd.Series:
    """Try each known date format; anything unparseable becomes NaT."""
    result = pd.Series(pd.NaT, index=series.index)
    for fmt in DATE_FORMATS:
        parsed = pd.to_datetime(series, format=fmt, errors="coerce")
        result = result.fillna(parsed)
    return result.dt.date


def to_number(series: pd.Series) -> pd.Series:
    """'€19.99' -> 19.99. Anything not a number becomes NaN."""
    cleaned = series.astype(str).str.replace("€", "", regex=False).str.replace(",", ".").str.strip()
    return pd.to_numeric(cleaned, errors="coerce")


def split(df: pd.DataFrame, bad_mask: pd.Series, reason: str, rejected: list):
    """Move rows matching bad_mask into the rejected list with a reason."""
    if bad_mask.any():
        bad = df[bad_mask].copy()
        bad["reject_reason"] = reason
        rejected.append(bad)
    return df[~bad_mask]


def finish(table: str, clean: pd.DataFrame, rejected: list, raw_count: int):
    rejected_df = pd.concat(rejected) if rejected else pd.DataFrame()
    log.info(f"TRANSFORM {table:<12} {raw_count:>6} in -> {len(clean):>6} clean, "
             f"{len(rejected_df):>4} rejected")
    return clean.reset_index(drop=True), rejected_df


# ---------- one function per table ----------

def transform_customers(df: pd.DataFrame):
    raw_count, rejected = len(df), []
    df = df.copy()

    df = split(df, df.duplicated(), "exact duplicate row", rejected)
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce")
    df = split(df, df["customer_id"].isna(), "invalid customer_id", rejected)
    df = split(df, df.duplicated("customer_id"), "duplicate customer_id", rejected)

    df["name"] = df["name"].str.strip()
    df = split(df, df["name"] == "", "missing name", rejected)

    # Missing email is allowed (stored as NULL), but formatting is fixed.
    df["email"] = df["email"].str.strip().str.lower().replace("", None)
    df = split(df, df["email"].notna() & df.duplicated("email"), "duplicate email", rejected)

    df["country"] = df["country"].str.strip().str.lower().map(COUNTRY_MAP).fillna(df["country"])
    df["signup_date"] = parse_dates(df["signup_date"])
    df = split(df, df["signup_date"].isna(), "invalid signup_date", rejected)

    df["customer_id"] = df["customer_id"].astype(int)
    return finish("customers", df, rejected, raw_count)


def transform_products(df: pd.DataFrame):
    raw_count, rejected = len(df), []
    df = df.copy()
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")
    df = split(df, df["product_id"].isna(), "invalid product_id", rejected)
    df = split(df, df.duplicated("product_id"), "duplicate product_id", rejected)

    df["price"] = to_number(df["price"])
    df["cost"] = to_number(df["cost"])
    df = split(df, df["price"].isna() | (df["price"] < 0), "invalid price", rejected)

    df["product_id"] = df["product_id"].astype(int)
    return finish("products", df, rejected, raw_count)


def transform_orders(df: pd.DataFrame, valid_customer_ids: set):
    raw_count, rejected = len(df), []
    df = df.copy()
    df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce")
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce")
    df = split(df, df["order_id"].isna(), "invalid order_id", rejected)
    df = split(df, df.duplicated("order_id"), "duplicate order_id", rejected)

    # Referential integrity: an order must belong to a real customer.
    df = split(df, ~df["customer_id"].isin(valid_customer_ids), "unknown customer_id", rejected)

    df["status"] = df["status"].str.strip().str.lower()
    df = split(df, ~df["status"].isin(VALID_STATUSES), "invalid status", rejected)

    df["order_date"] = parse_dates(df["order_date"])
    df = split(df, df["order_date"].isna(), "invalid order_date", rejected)
    df = split(df, df["order_date"] > pd.Timestamp.today().date(), "order_date in the future", rejected)

    df[["order_id", "customer_id"]] = df[["order_id", "customer_id"]].astype(int)
    return finish("orders", df, rejected, raw_count)


def transform_order_items(df: pd.DataFrame, valid_order_ids: set, valid_product_ids: set):
    raw_count, rejected = len(df), []
    df = df.copy()
    for col in ["order_item_id", "order_id", "product_id", "quantity"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["unit_price"] = to_number(df["unit_price"])

    df = split(df, df.duplicated("order_item_id"), "duplicate order_item_id", rejected)
    df = split(df, ~df["order_id"].isin(valid_order_ids), "unknown or rejected order_id", rejected)
    df = split(df, ~df["product_id"].isin(valid_product_ids), "unknown product_id", rejected)
    df = split(df, df["quantity"].isna() | (df["quantity"] <= 0), "quantity not positive", rejected)
    df = split(df, df["unit_price"].isna() | (df["unit_price"] < 0), "invalid unit_price", rejected)

    for col in ["order_item_id", "order_id", "product_id", "quantity"]:
        df[col] = df[col].astype(int)
    return finish("order_items", df, rejected, raw_count)


def transform_employees(df: pd.DataFrame):
    raw_count, rejected = len(df), []
    df = df.copy()
    df["employee_id"] = pd.to_numeric(df["employee_id"], errors="coerce")
    df["salary"] = pd.to_numeric(df["salary"], errors="coerce")
    df = split(df, df.duplicated("employee_id"), "duplicate employee_id", rejected)
    df = split(df, df["salary"].isna() | (df["salary"] <= 0), "invalid salary", rejected)
    df["hire_date"] = parse_dates(df["hire_date"])
    df = split(df, df["hire_date"].isna(), "invalid hire_date", rejected)

    df[["employee_id", "salary"]] = df[["employee_id", "salary"]].astype(int)
    return finish("employees", df, rejected, raw_count)


def transform_all(raw: dict[str, pd.DataFrame]):
    """Run all transforms in dependency order (parents before children)."""
    clean, rejected = {}, {}
    clean["customers"], rejected["customers"] = transform_customers(raw["customers"])
    clean["products"], rejected["products"] = transform_products(raw["products"])
    clean["orders"], rejected["orders"] = transform_orders(
        raw["orders"], set(clean["customers"]["customer_id"]))
    clean["order_items"], rejected["order_items"] = transform_order_items(
        raw["order_items"], set(clean["orders"]["order_id"]), set(clean["products"]["product_id"]))

    # An order whose items were ALL rejected is an empty order: reject it too.
    orders, extra = clean["orders"], []
    orders = split(orders, ~orders["order_id"].isin(clean["order_items"]["order_id"]),
                   "no valid order items", extra)
    if extra:
        log.info(f"TRANSFORM orders       {len(extra[0]):>6} more rejected (no valid items left)")
        clean["orders"] = orders.reset_index(drop=True)
        rejected["orders"] = pd.concat([rejected["orders"], *extra])

    clean["employees"], rejected["employees"] = transform_employees(raw["employees"])
    return clean, rejected

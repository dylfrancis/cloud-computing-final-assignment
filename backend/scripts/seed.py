"""Seed the database from the three CSVs in backend/data/.

Usage:
    python -m scripts.seed # truncate + load (default)
    python -m scripts.seed --append # skip truncate, just insert
    python -m scripts.seed --batch 2000 # override transaction batch size

Run `python -m alembic upgrade head` first so the tables exist.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import get_settings, sync_database_url
from app.models.household import Household
from app.models.product import Product
from app.models.transaction import Transaction

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HOUSEHOLD_CSV = DATA_DIR / "400_households.csv"
PRODUCT_CSV = DATA_DIR / "400_products.csv"
TRANSACTION_CSV = DATA_DIR / "400_transactions.csv"


def _read_csv_clean(path: Path) -> pd.DataFrame:
    """Read a CSV whose headers and values are padded with whitespace.

    Every column is read as string, stripped, and 'null'/'' become None.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].str.strip().replace({"null": None, "": None, "NULL": None})
    return df


def load_households() -> list[dict]:
    df = _read_csv_clean(HOUSEHOLD_CSV).rename(
        columns={
            "HSHD_NUM": "hshd_num",
            "L": "loyalty_flag",
            "AGE_RANGE": "age_range",
            "MARITAL": "marital_status",
            "INCOME_RANGE": "income_range",
            "HOMEOWNER": "homeowner_desc",
            "HSHD_COMPOSITION": "household_composition",
            "HH_SIZE": "household_size",
            "CHILDREN": "children",
        }
    )
    df["hshd_num"] = df["hshd_num"].astype(int)
    # Dedupe in case of repeated HSHD_NUM rows in the source.
    df = df.drop_duplicates(subset=["hshd_num"], keep="first")
    return df.to_dict(orient="records")


def load_products() -> list[dict]:
    df = _read_csv_clean(PRODUCT_CSV).rename(
        columns={
            "PRODUCT_NUM": "product_num",
            "DEPARTMENT": "department",
            "COMMODITY": "commodity",
            "BRAND_TY": "brand_type",
            "NATURAL_ORGANIC_FLAG": "natural_organic_flag",
        }
    )
    df["product_num"] = df["product_num"].astype(int)
    df = df.drop_duplicates(subset=["product_num"], keep="first")
    return df.to_dict(orient="records")


def load_transactions(valid_hshds: set[int], valid_products: set[int]) -> list[dict]:
    df = _read_csv_clean(TRANSACTION_CSV).rename(
        columns={
            "BASKET_NUM": "basket_num",
            "HSHD_NUM": "hshd_num",
            "PURCHASE_": "purchase_date",
            "PRODUCT_NUM": "product_num",
            "SPEND": "spend",
            "UNITS": "units",
            "STORE_R": "store_region",
            "WEEK_NUM": "week_num",
            "YEAR": "year",
        }
    )

    df["hshd_num"] = df["hshd_num"].astype(int)
    df["product_num"] = df["product_num"].astype(int)
    df["basket_num"] = df["basket_num"].astype(int)
    df["units"] = pd.to_numeric(df["units"], errors="coerce").fillna(0).astype(int)
    df["spend"] = pd.to_numeric(df["spend"], errors="coerce").fillna(0.0)
    df["purchase_date"] = pd.to_datetime(df["purchase_date"], format="%d-%b-%y").dt.date
    df["week_num"] = pd.to_numeric(df["week_num"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    before = len(df)
    df = df[df["hshd_num"].isin(valid_hshds) & df["product_num"].isin(valid_products)]
    dropped = before - len(df)
    if dropped:
        print(f"  WARN: dropped {dropped} transactions with unknown hshd_num/product_num")

    records = df.to_dict(orient="records")
    for r in records:
        for k, v in r.items():
            if v is pd.NaT or (isinstance(v, float) and pd.isna(v)):
                r[k] = None
            elif k in ("week_num", "year") and isinstance(v, float):
                r[k] = int(v)
    return records


def ensure_schema(engine: Engine) -> None:
    existing = set(inspect(engine).get_table_names())
    missing = {"households", "products", "transactions"} - existing
    if missing:
        raise SystemExit(
            f"Missing tables: {sorted(missing)}. Run `python -m alembic upgrade head` first."
        )


def truncate(session: Session) -> None:
    # FK order: children before parents.
    session.execute(text("DELETE FROM transactions"))
    session.execute(text("DELETE FROM products"))
    session.execute(text("DELETE FROM households"))
    session.commit()


def bulk_insert(session: Session, model, rows: list[dict], batch: int = 5000) -> None:
    total = len(rows)
    if total == 0:
        return
    for i in range(0, total, batch):
        chunk = rows[i : i + batch]
        session.bulk_insert_mappings(model, chunk)
        session.commit()
        done = min(i + batch, total)
        if total > batch:
            print(f"    {done}/{total}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--append", action="store_true", help="Skip truncate before loading")
    parser.add_argument("--batch", type=int, default=1000, help="Transactions per insert batch")
    args = parser.parse_args()

    settings = get_settings()
    url = sync_database_url(settings.database_url)
    engine = create_engine(url, fast_executemany=True)

    ensure_schema(engine)

    print("Reading CSVs...")
    households = load_households()
    products = load_products()
    valid_hshds = {h["hshd_num"] for h in households}
    valid_products = {p["product_num"] for p in products}
    transactions = load_transactions(valid_hshds, valid_products)
    print(
        f"  households={len(households)}  products={len(products)}  "
        f"transactions={len(transactions)}"
    )

    with Session(engine) as session:
        if not args.append:
            print("Truncating tables...")
            truncate(session)

        print(f"Inserting {len(households)} households...")
        bulk_insert(session, Household, households)

        print(f"Inserting {len(products)} products...")
        bulk_insert(session, Product, products)

        print(f"Inserting {len(transactions)} transactions (batch={args.batch})...")
        started = time.perf_counter()
        bulk_insert(session, Transaction, transactions, batch=args.batch)
        elapsed = time.perf_counter() - started
        print(f"  transactions inserted in {elapsed:.1f}s")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

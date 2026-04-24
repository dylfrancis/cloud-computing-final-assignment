"""Seed the database from the three CSVs in backend/data/.

Usage:
    python -m scripts.seed                 # truncate + load (default)
    python -m scripts.seed --append        # skip truncate, just insert
    python -m scripts.seed --batch 2000    # override transaction batch size

Run `python -m alembic upgrade head` first so the tables exist.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import get_settings, sync_database_url
from app.data_load import (
    bulk_insert,
    load_households,
    load_products,
    load_transactions,
    truncate_retail_tables,
)
from app.models.household import Household
from app.models.product import Product
from app.models.transaction import Transaction

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HOUSEHOLD_CSV = DATA_DIR / "400_households.csv"
PRODUCT_CSV = DATA_DIR / "400_products.csv"
TRANSACTION_CSV = DATA_DIR / "400_transactions.csv"


def ensure_schema(engine: Engine) -> None:
    existing = set(inspect(engine).get_table_names())
    missing = {"households", "products", "transactions"} - existing
    if missing:
        raise SystemExit(
            f"Missing tables: {sorted(missing)}. Run `python -m alembic upgrade head` first."
        )


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
    households = load_households(HOUSEHOLD_CSV)
    products = load_products(PRODUCT_CSV)
    valid_hshds = {h["hshd_num"] for h in households}
    valid_products = {p["product_num"] for p in products}
    transactions, dropped = load_transactions(TRANSACTION_CSV, valid_hshds, valid_products)
    if dropped:
        print(f"  WARN: dropped {dropped} transactions with unknown hshd_num/product_num")
    print(
        f"  households={len(households)}  products={len(products)}  "
        f"transactions={len(transactions)}"
    )

    with Session(engine) as session:
        if not args.append:
            print("Truncating tables...")
            truncate_retail_tables(session)

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

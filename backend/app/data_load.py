"""Shared CSV ingestion helpers used by both `scripts/seed.py` and the
`POST /uploads` router.

Each loader reads a CSV produced by the course's 84.51° dataset (headers and
values padded with whitespace, sentinel ``null`` strings, mixed types) and
returns a list of dicts shaped for ``bulk_insert_mappings`` into the
corresponding ORM model.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


def read_csv_clean(path: Path) -> pd.DataFrame:
    """Read a course CSV, strip whitespace, and normalise ``null`` sentinels."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].str.strip().replace({"null": None, "": None, "NULL": None})
    return df


def load_households(path: Path) -> list[dict]:
    df = read_csv_clean(path).rename(
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
    df = df.drop_duplicates(subset=["hshd_num"], keep="first")
    return df.to_dict(orient="records")


def load_products(path: Path) -> list[dict]:
    df = read_csv_clean(path).rename(
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


def load_transactions(
    path: Path, valid_hshds: set[int], valid_products: set[int]
) -> tuple[list[dict], int]:
    """Return (records, dropped_count).

    Rows that reference unknown households or products are dropped (FK safety).
    """
    df = read_csv_clean(path).rename(
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

    records = df.to_dict(orient="records")
    for r in records:
        for k, v in r.items():
            if v is pd.NaT or (isinstance(v, float) and pd.isna(v)):
                r[k] = None
            elif k in ("week_num", "year") and isinstance(v, float):
                r[k] = int(v)
    return records, dropped


def truncate_retail_tables(session: Session) -> None:
    """Delete transactions, then products, then households (FK order)."""
    session.execute(text("DELETE FROM transactions"))
    session.execute(text("DELETE FROM products"))
    session.execute(text("DELETE FROM households"))
    session.commit()


def bulk_insert(session: Session, model, rows: list[dict], batch: int = 1000) -> None:
    total = len(rows)
    if total == 0:
        return
    for i in range(0, total, batch):
        chunk = rows[i : i + batch]
        session.bulk_insert_mappings(model, chunk)
        session.commit()

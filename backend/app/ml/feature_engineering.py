"""Feature engineering for ML models."""

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import Household
from app.models.product import Product
from app.models.transaction import Transaction

# Default lookback window for training/prediction feature pulls. The 84.51°
# sample is from 2018-2020; against live timestamps in 2026+ a 1-year window
# excludes every transaction. 20 years keeps the historical demo data in play
# without affecting anyone running the models against fresh retail feeds.
DEFAULT_LOOKBACK_DAYS = 365 * 20


async def get_reference_date(session: AsyncSession) -> pd.Timestamp:
    """Return the most recent purchase_date in the transactions table.

    We use this as the "current date" anchor for recency / future-window
    calculations so the models still produce meaningful targets when trained
    on a historical snapshot (the 84.51° sample ends 2020-08-15). Falls back
    to today if the table is empty.
    """
    result = await session.execute(select(func.max(Transaction.purchase_date)))
    max_date = result.scalar_one_or_none()
    if max_date is None:
        return pd.Timestamp.now().normalize()
    return pd.Timestamp(max_date)


async def get_clv_features(
    session: AsyncSession, hshd_num: int | None = None, lookback_days: int = DEFAULT_LOOKBACK_DAYS
) -> pd.DataFrame:
    """
    Extract features for CLV (Customer Lifetime Value) prediction.

    Features:
    - total_spend: Sum of all transactions
    - transaction_count: Number of transactions
    - avg_spend_per_transaction: Average spend per transaction
    - recency_days: Days since last purchase
    - purchase_frequency: Transactions per 30 days
    - avg_basket_size: Average units per transaction
    - dept_diversity: Number of different departments purchased
    - product_diversity: Number of different products purchased
    - Demographics: age_range, income_range, household_size, children, loyalty_flag

    Returns DataFrame with columns matching feature names, indexed by hshd_num.
    """
    cutoff_date = datetime.now() - timedelta(days=lookback_days)

    # Build base query for transactions
    tx_query = (
        select(
            Transaction.hshd_num,
            Transaction.spend,
            Transaction.units,
            Transaction.purchase_date,
            Product.department,
        )
        .join(Product, Product.product_num == Transaction.product_num)
        .where(Transaction.purchase_date >= cutoff_date.date())
    )

    if hshd_num is not None:
        tx_query = tx_query.where(Transaction.hshd_num == hshd_num)

    result = await session.execute(tx_query)
    transactions = pd.DataFrame(result.mappings().all())

    if transactions.empty:
        return pd.DataFrame()

    # pyodbc hands Numeric(10,2) back as decimal.Decimal; downstream sklearn
    # math expects floats, so normalise once here.
    transactions["spend"] = transactions["spend"].astype(float)

    # Aggregate transaction-level features
    agg_features = transactions.groupby("hshd_num").agg({
        "spend": ["sum", "count", "mean"],
        "units": ["mean"],
        "department": "nunique",
    }).reset_index()

    agg_features.columns = [
        "hshd_num",
        "total_spend",
        "transaction_count",
        "avg_spend_per_transaction",
        "avg_basket_size",
        "dept_diversity",
    ]

    # Product diversity: count distinct products per household
    product_query = (
        select(
            Transaction.hshd_num,
            func.count(Transaction.product_num.distinct()).label("product_diversity"),
        )
        .where(Transaction.purchase_date >= cutoff_date.date())
        .group_by(Transaction.hshd_num)
    )

    if hshd_num is not None:
        product_query = product_query.where(Transaction.hshd_num == hshd_num)

    result = await session.execute(product_query)
    product_div = pd.DataFrame(result.mappings().all())
    agg_features = agg_features.merge(product_div, on="hshd_num", how="left")

    # Recency: days since last purchase
    recency_query = (
        select(
            Transaction.hshd_num,
            func.max(Transaction.purchase_date).label("last_purchase_date"),
        )
        .group_by(Transaction.hshd_num)
    )

    if hshd_num is not None:
        recency_query = recency_query.where(Transaction.hshd_num == hshd_num)

    result = await session.execute(recency_query)
    recency = pd.DataFrame(result.mappings().all())
    # pd.to_datetime normalises the date objects coming out of pyodbc so the
    # subtraction produces a Timedelta Series with a working .dt accessor.
    recency["last_purchase_date"] = pd.to_datetime(recency["last_purchase_date"])
    reference_date = await get_reference_date(session)
    recency["recency_days"] = (reference_date - recency["last_purchase_date"]).dt.days
    recency = recency[["hshd_num", "recency_days"]]
    agg_features = agg_features.merge(recency, on="hshd_num", how="left")

    # Purchase frequency: transactions per 30 days
    agg_features["purchase_frequency"] = (
        agg_features["transaction_count"] / (lookback_days / 30)
    )

    # Demographics from households table
    if hshd_num is not None:
        demo_query = select(Household).where(Household.hshd_num == hshd_num)
    else:
        # Get all households in our transaction set
        hshd_nums = agg_features["hshd_num"].tolist()
        demo_query = select(Household).where(Household.hshd_num.in_(hshd_nums))

    result = await session.execute(demo_query)
    demographics = pd.DataFrame(
        [h.__dict__ for h in result.scalars().all()]
    ).drop(columns=["_sa_instance_state"], errors="ignore")

    # Merge demographics
    agg_features = agg_features.merge(demographics, on="hshd_num", how="left")

    # Encode categorical demographics
    agg_features = _encode_demographics(agg_features)

    # Handle missing values
    agg_features = agg_features.fillna(0)

    return agg_features.set_index("hshd_num")


async def get_churn_features(
    session: AsyncSession, hshd_num: int | None = None, lookback_days: int = DEFAULT_LOOKBACK_DAYS
) -> pd.DataFrame:
    """
    Extract features for Churn prediction.

    Features:
    - recency_days: Days since last purchase
    - frequency_recent: Transactions in last 90 days
    - frequency_prior: Transactions in 91-365 days
    - frequency_decline: Ratio of recent to prior frequency
    - spend_recent: Total spend in last 90 days
    - spend_prior: Total spend in 91-365 days
    - spend_decline: Ratio of recent to prior spending
    - dept_diversity: Number of unique departments
    - loyalty_flag: Whether customer has loyalty flag

    Returns DataFrame with columns matching feature names, indexed by hshd_num.
    """
    cutoff_date = datetime.now() - timedelta(days=lookback_days)
    recent_cutoff = datetime.now() - timedelta(days=90)

    tx_query = (
        select(
            Transaction.hshd_num,
            Transaction.spend,
            Transaction.purchase_date,
            Product.department,
        )
        .join(Product, Product.product_num == Transaction.product_num)
        .where(Transaction.purchase_date >= cutoff_date.date())
    )

    if hshd_num is not None:
        tx_query = tx_query.where(Transaction.hshd_num == hshd_num)

    result = await session.execute(tx_query)
    transactions = pd.DataFrame(result.mappings().all())

    if transactions.empty:
        return pd.DataFrame()

    # Decimal → float so downstream aggregates don't mix dtypes.
    transactions["spend"] = transactions["spend"].astype(float)

    # Recency
    recency_query = (
        select(
            Transaction.hshd_num,
            func.max(Transaction.purchase_date).label("last_purchase_date"),
        )
        .group_by(Transaction.hshd_num)
    )

    if hshd_num is not None:
        recency_query = recency_query.where(Transaction.hshd_num == hshd_num)

    result = await session.execute(recency_query)
    recency = pd.DataFrame(result.mappings().all())
    # pd.to_datetime normalises the date objects coming out of pyodbc so the
    # subtraction produces a Timedelta Series with a working .dt accessor.
    recency["last_purchase_date"] = pd.to_datetime(recency["last_purchase_date"])
    reference_date = await get_reference_date(session)
    recency["recency_days"] = (reference_date - recency["last_purchase_date"]).dt.days
    recency = recency[["hshd_num", "recency_days"]]

    # Split into recent and prior periods
    transactions["is_recent"] = transactions["purchase_date"] >= recent_cutoff.date()

    # Recent period (last 90 days)
    recent_tx = transactions[transactions["is_recent"]]
    recent_agg = recent_tx.groupby("hshd_num").agg({
        "spend": "sum",
        "purchase_date": "count",
        "department": "nunique",
    }).reset_index()
    recent_agg.columns = ["hshd_num", "spend_recent", "frequency_recent", "dept_diversity"]

    # Prior period (91-365 days)
    prior_tx = transactions[~transactions["is_recent"]]
    prior_agg = prior_tx.groupby("hshd_num").agg({
        "spend": "sum",
        "purchase_date": "count",
    }).reset_index()
    prior_agg.columns = ["hshd_num", "spend_prior", "frequency_prior"]

    # Merge periods
    features = recent_agg.merge(prior_agg, on="hshd_num", how="outer")
    features = features.fillna(0)

    # Calculate decline metrics (avoid division by zero)
    features["frequency_decline"] = np.where(
        features["frequency_prior"] > 0,
        features["frequency_recent"] / features["frequency_prior"],
        0,
    )
    features["spend_decline"] = np.where(
        features["spend_prior"] > 0,
        features["spend_recent"] / features["spend_prior"],
        0,
    )

    # Add recency
    features = features.merge(recency, on="hshd_num", how="left")

    # Add loyalty flag from demographics
    if hshd_num is not None:
        demo_query = select(Household.hshd_num, Household.loyalty_flag).where(
            Household.hshd_num == hshd_num
        )
    else:
        hshd_nums = features["hshd_num"].tolist()
        demo_query = select(Household.hshd_num, Household.loyalty_flag).where(
            Household.hshd_num.in_(hshd_nums)
        )

    result = await session.execute(demo_query)
    loyalty = pd.DataFrame(result.mappings().all())
    loyalty["loyalty_flag"] = (loyalty["loyalty_flag"] == "Y").astype(int)
    features = features.merge(loyalty, on="hshd_num", how="left")
    features["loyalty_flag"] = features["loyalty_flag"].fillna(0)

    return features.set_index("hshd_num")


async def get_market_basket_features(
    session: AsyncSession, lookback_days: int = DEFAULT_LOOKBACK_DAYS, min_support: float = 0.02
) -> pd.DataFrame:
    """Mine frequent product pairs with FP-growth on a sparse basket matrix.

    Output DataFrame (kept identical to the previous nested-loop implementation
    so ``BasketModel.predict`` doesn't need changes):

    - product1, product2: Product identifiers, sorted so product1 < product2
    - co_occurrence: Number of baskets containing both
    - support: Fraction of total baskets

    We use ``mlxtend.frequent_patterns.fpgrowth`` against a sparse one-hot
    transaction matrix — dramatically lighter on memory than materialising
    every product pair in Python and safe to run on a B1 App Service
    (1.75 GB RAM) even with 250k+ baskets.
    """
    from mlxtend.frequent_patterns import fpgrowth
    from mlxtend.preprocessing import TransactionEncoder

    cutoff_date = datetime.now() - timedelta(days=lookback_days)

    basket_query = (
        select(Transaction.basket_num, Transaction.product_num)
        .where(Transaction.purchase_date >= cutoff_date.date())
    )

    result = await session.execute(basket_query)
    baskets = pd.DataFrame(result.mappings().all())

    if baskets.empty:
        return pd.DataFrame()

    # basket → list of unique product_nums
    basket_lists: list[list[int]] = (
        baskets.groupby("basket_num")["product_num"].agg(lambda s: list(set(s))).tolist()
    )
    total_baskets = len(basket_lists)

    # Sparse one-hot. TransactionEncoder with sparse=True returns a scipy
    # csr_matrix; the SparseDataFrame wrapper is what fpgrowth expects.
    # mlxtend requires string column names on sparse frames, so we cast the
    # product_num ints to str and back after mining.
    te = TransactionEncoder()
    te_array = te.fit(basket_lists).transform(basket_lists, sparse=True)
    sparse_df = pd.DataFrame.sparse.from_spmatrix(
        te_array, columns=[str(c) for c in te.columns_]
    )

    # max_len=2 restricts FP-growth to singletons + pairs — everything we
    # need for the pair-wise recommendation path in BasketModel.predict.
    frequent = fpgrowth(sparse_df, min_support=min_support, use_colnames=True, max_len=2)

    if frequent.empty:
        return pd.DataFrame()

    # Keep only 2-itemsets; drop singleton support rows.
    pairs = frequent[frequent["itemsets"].apply(len) == 2].copy()
    if pairs.empty:
        return pd.DataFrame()

    def _split(itemset: frozenset[str]) -> pd.Series:
        # itemset elements came in as str (see column-cast above); convert
        # back to int so the DataFrame product ids match Transaction.product_num.
        a, b = sorted(int(x) for x in itemset)
        return pd.Series([a, b])

    pairs[["product1", "product2"]] = pairs["itemsets"].apply(_split)
    pairs["co_occurrence"] = (pairs["support"] * total_baskets).round().astype(int)
    assoc_df = pairs[["product1", "product2", "co_occurrence", "support"]].reset_index(drop=True)
    return assoc_df


def _encode_demographics(df: pd.DataFrame) -> pd.DataFrame:
    """Encode categorical demographic features."""
    encoding_maps = {
        "age_range": {
            "19-24": 1, "25-34": 2, "35-44": 3, "45-54": 4, "55-64": 5, "65+": 6
        },
        "income_range": {
            "$12,499": 1, "$12,500-24,999": 2, "$25,000-49,999": 3,
            "$50,000-74,999": 4, "$75,000-99,999": 5, "$100,000+": 6
        },
        "household_size": {
            "1": 1, "2": 2, "3": 3, "4": 4, "5+": 5
        },
        "marital_status": {"A": 0, "B": 1, "U": 2},
        "homeowner_desc": {"Homeowner": 1, "Renter": 0, "Unknown": -1},
        "children": {"0": 0, "1": 1, "2": 2, "3+": 3},
        "loyalty_flag": {"Y": 1, "N": 0},
    }

    for col, mapping in encoding_maps.items():
        if col in df.columns:
            df[col] = df[col].map(mapping).fillna(-1).astype(int)

    return df


def prepare_training_data(
    features_df: pd.DataFrame, target_series: pd.Series | None = None
) -> tuple[np.ndarray, np.ndarray | None]:
    """
    Prepare feature data for model training.

    Handles:
    - Dropping non-numeric columns
    - Filling NaN with 0
    - Normalizing features to [0, 1]

    Returns:
    - X: Feature matrix (n_samples, n_features)
    - y: Target vector (if provided) or None
    """
    # Select only numeric columns
    X = features_df.select_dtypes(include=[np.number]).fillna(0)

    # Normalize to [0, 1]
    col_max = X.max()
    col_max[col_max == 0] = 1  # Avoid division by zero
    X = X / col_max

    y = None
    if target_series is not None:
        y = target_series.values

    return X.values, y

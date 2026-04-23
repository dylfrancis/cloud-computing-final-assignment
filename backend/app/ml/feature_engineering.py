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


async def get_clv_features(
    session: AsyncSession, hshd_num: int | None = None, lookback_days: int = 365
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
    recency["recency_days"] = (datetime.now().date() - recency["last_purchase_date"]).dt.days
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
    session: AsyncSession, hshd_num: int | None = None, lookback_days: int = 365
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
    recency["recency_days"] = (datetime.now().date() - recency["last_purchase_date"]).dt.days
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
    session: AsyncSession, lookback_days: int = 365, min_support: float = 0.02
) -> pd.DataFrame:
    """
    Extract features for market basket analysis.

    Returns product association rules: {product_a: {product_b: co_occurrence_count}}
    This can be used for itemset mining and association rule generation.

    Returns DataFrame with columns:
    - product1, product2: Product identifiers
    - co_occurrence: Number of baskets containing both
    - support: Fraction of total baskets
    """
    cutoff_date = datetime.now() - timedelta(days=lookback_days)

    # Get all basket compositions
    basket_query = (
        select(
            Transaction.basket_num,
            Transaction.hshd_num,
            Transaction.product_num,
            Product.department,
            Product.commodity,
        )
        .join(Product, Product.product_num == Transaction.product_num)
        .where(Transaction.purchase_date >= cutoff_date.date())
        .order_by(Transaction.basket_num, Transaction.product_num)
    )

    result = await session.execute(basket_query)
    baskets = pd.DataFrame(result.mappings().all())

    if baskets.empty:
        return pd.DataFrame()

    # Count total unique baskets
    total_baskets = baskets["basket_num"].nunique()

    # Find product co-occurrences: products purchased in same basket
    basket_items = (
        baskets.groupby("basket_num")["product_num"]
        .apply(list)
        .reset_index()
    )

    associations = []
    for items in basket_items["product_num"]:
        # All pairs in this basket
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                product_a, product_b = min(items[i], items[j]), max(items[i], items[j])
                associations.append({"product1": product_a, "product2": product_b})

    if not associations:
        return pd.DataFrame()

    assoc_df = pd.DataFrame(associations)
    assoc_df = assoc_df.groupby(["product1", "product2"]).size().reset_index(name="co_occurrence")
    assoc_df["support"] = assoc_df["co_occurrence"] / total_baskets

    # Filter by minimum support
    assoc_df = assoc_df[assoc_df["support"] >= min_support]

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

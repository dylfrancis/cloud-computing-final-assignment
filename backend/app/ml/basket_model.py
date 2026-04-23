"""Market basket analysis for product cross-selling."""

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.feature_engineering import get_market_basket_features


class BasketModel:
    """Market basket analysis for identifying cross-selling opportunities."""

    def __init__(self):
        """Initialize basket model."""
        self.associations: pd.DataFrame | None = None

    async def train(
        self, session: AsyncSession, lookback_days: int = 365, min_support: float = 0.02
    ) -> dict:
        """
        Train market basket model by finding product associations.

        Args:
            session: Database session
            lookback_days: Historical window for transactions
            min_support: Minimum fraction of baskets (0-1)

        Returns:
            Training summary: n_associations, top_rules
        """
        self.associations = await get_market_basket_features(
            session, lookback_days=lookback_days, min_support=min_support
        )

        if self.associations.empty:
            return {
                "n_associations": 0,
                "top_rules": [],
                "note": "No significant product associations found",
            }

        # Sort by co-occurrence frequency
        top_associations = self.associations.nlargest(10, "co_occurrence")

        return {
            "n_associations": len(self.associations),
            "min_support": min_support,
            "top_rules": top_associations[["product1", "product2", "co_occurrence", "support"]]
            .to_dict("records"),
        }

    async def predict(self, session: AsyncSession, hshd_num: int, limit: int = 5) -> dict:
        """
        Get product recommendations for a household based on market basket analysis.

        Strategy: Find products the household has purchased, then recommend
        products frequently co-purchased with those items.

        Args:
            session: Database session
            hshd_num: Household to recommend for
            limit: Max number of recommendations

        Returns:
            {
                "hshd_num": int,
                "recommendations": [
                    {"product_id": int, "score": float, "reason": str}
                ]
            }
        """
        if self.associations is None or self.associations.empty:
            raise ValueError("Model not trained. Call train() first.")

        from sqlalchemy import select

        from app.models.transaction import Transaction

        # Get products household has purchased
        query = select(Transaction.product_num.distinct()).where(
            Transaction.hshd_num == hshd_num
        )
        result = await session.execute(query)
        purchased_products = set(r[0] for r in result.all())

        if not purchased_products:
            return {"hshd_num": hshd_num, "recommendations": []}

        # Find products frequently co-purchased
        # Score = support of the rule (higher = more common)
        recommendations = {}

        for _, row in self.associations.iterrows():
            product1, product2 = row["product1"], row["product2"]
            support = row["support"]

            # If household bought product1, recommend product2
            if product1 in purchased_products and product2 not in purchased_products:
                recommendations[product2] = max(recommendations.get(product2, 0), support)

            # If household bought product2, recommend product1
            if product2 in purchased_products and product1 not in purchased_products:
                recommendations[product1] = max(recommendations.get(product1, 0), support)

        # Sort by score and limit
        top_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:limit]

        return {
            "hshd_num": hshd_num,
            "recommendations": [
                {"product_id": int(prod), "score": float(score), "reason": "Co-purchase frequency"}
                for prod, score in top_recs
            ],
        }

"""CLV (Customer Lifetime Value) model training and prediction."""

import io
import pickle
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.feature_engineering import get_clv_features, prepare_training_data


class CLVModel:
    """Gradient Boosting model for predicting Customer Lifetime Value."""

    def __init__(self, model: GradientBoostingRegressor | None = None):
        """Initialize with existing model or create new."""
        self.model = model or GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
        )
        self.is_trained = model is not None
        self.feature_names: list[str] | None = None
        self.training_date: datetime | None = None

    async def train(
        self,
        session: AsyncSession,
        lookback_days: int = 365,
        future_days: int = 90,
        test_size: float = 0.2,
    ) -> dict:
        """
        Train the CLV model on historical data.

        Args:
            session: Database session
            lookback_days: Historical window for features
            future_days: Future window for target CLV
            test_size: Train/test split ratio

        Returns:
            Training metrics: mse, rmse, r2_score
        """
        # Get current features
        features_df = await get_clv_features(session, lookback_days=lookback_days)

        if features_df.empty:
            raise ValueError("No transaction data available for training")

        # Calculate target: spending in the LAST future_days period of the
        # dataset. Anchoring on MAX(purchase_date) instead of "now" makes the
        # target well-defined even on a historical snapshot.
        target_query = f"""
            SELECT hshd_num, SUM(spend) as future_spend
            FROM transactions
            WHERE purchase_date >= DATEADD(
                day, -{future_days},
                (SELECT MAX(purchase_date) FROM transactions)
            )
            GROUP BY hshd_num
        """

        # Use raw SQL for efficiency (async not required for read-only)
        from sqlalchemy import text

        result = await session.execute(text(target_query))
        target_data = pd.DataFrame(result.mappings().all())

        if target_data.empty:
            raise ValueError("No future spend data available for training")

        # SUM(spend) comes back from pyodbc as decimal.Decimal; sklearn needs
        # floats for arithmetic downstream (metric computation).
        target_data["future_spend"] = target_data["future_spend"].astype(float)
        target_data = target_data.set_index("hshd_num")

        # Align features with target
        common_idx = features_df.index.intersection(target_data.index)
        X_aligned = features_df.loc[common_idx]
        y_aligned = target_data.loc[common_idx, "future_spend"]

        if len(common_idx) < 10:
            raise ValueError(f"Insufficient training samples: {len(common_idx)}")

        # Prepare data
        X, y = prepare_training_data(X_aligned, y_aligned)
        self.feature_names = list(X_aligned.columns)

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        # Train model
        self.model.fit(X_train, y_train)
        self.is_trained = True
        self.training_date = datetime.now()

        # Evaluate
        y_pred = self.model.predict(X_test)
        mse = np.mean((y_test - y_pred) ** 2)
        rmse = np.sqrt(mse)
        r2 = self.model.score(X_test, y_test)

        return {
            "mse": float(mse),
            "rmse": float(rmse),
            "r2_score": float(r2),
            "training_date": self.training_date.isoformat(),
            "n_samples": len(common_idx),
            "n_features": X.shape[1],
        }

    async def predict(self, session: AsyncSession, hshd_num: int) -> dict:
        """
        Predict CLV for a household.

        Returns:
            {
                "hshd_num": int,
                "clv_score": float (dollars),
                "clv_percentile": float (0-100),
                "segment": str ("high" | "medium" | "low"),
            }
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")

        features_df = await get_clv_features(session, hshd_num=hshd_num)

        if features_df.empty:
            raise ValueError(f"No transaction data for household {hshd_num}")

        X, _ = prepare_training_data(
            features_df[self.feature_names] if self.feature_names else features_df
        )

        clv_score = float(self.model.predict(X)[0])

        # Get percentile from all households for context
        all_features = await get_clv_features(session)
        all_X, _ = prepare_training_data(
            all_features[self.feature_names] if self.feature_names else all_features
        )
        all_scores = self.model.predict(all_X)
        # Percentile rank in [0, 100]: percent of household scores <= this one.
        # np.percentileofscore doesn't exist — scipy.stats has that function,
        # not numpy. We compute it inline to avoid pulling scipy.
        if len(all_scores) > 0:
            percentile = float(np.mean(all_scores <= clv_score) * 100)
        else:
            percentile = 0.0

        # Segment based on percentiles
        if percentile >= 66:
            segment = "high"
        elif percentile >= 33:
            segment = "medium"
        else:
            segment = "low"

        return {
            "hshd_num": hshd_num,
            "clv_score": clv_score,
            "clv_percentile": percentile,
            "segment": segment,
        }

    def save(self) -> bytes:
        """Serialize model to bytes for storage."""
        return pickle.dumps(
            {
                "model": self.model,
                "feature_names": self.feature_names,
                "training_date": self.training_date,
            }
        )

    @classmethod
    def load(cls, data: bytes) -> "CLVModel":
        """Deserialize model from bytes."""
        obj = pickle.loads(data)
        instance = cls(model=obj["model"])
        instance.feature_names = obj["feature_names"]
        instance.training_date = obj["training_date"]
        instance.is_trained = True
        return instance

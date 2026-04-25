"""Churn prediction model training and prediction."""

import pickle
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.feature_engineering import get_churn_features, prepare_training_data


class ChurnModel:
    """Gradient Boosting classifier for predicting customer churn risk."""

    def __init__(self, model: GradientBoostingClassifier | None = None):
        """Initialize with existing model or create new."""
        self.model = model or GradientBoostingClassifier(
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
        churn_threshold_days: int = 180,
        test_size: float = 0.2,
    ) -> dict:
        """
        Train churn prediction model.

        A household is labeled as "churned" if they had no purchases in the
        last churn_threshold_days.

        Args:
            session: Database session
            lookback_days: Historical window for features
            churn_threshold_days: Days of inactivity to label as churn
            test_size: Train/test split ratio

        Returns:
            Training metrics: accuracy, precision, recall, auc, f1
        """
        from sqlalchemy import text

        # Get features. observation_lag_days MUST match churn_threshold_days
        # so features come from BEFORE the label window — otherwise the label
        # leaks into the features and the GBT saturates to 0/100 outputs.
        features_df = await get_churn_features(
            session,
            lookback_days=lookback_days,
            observation_lag_days=churn_threshold_days,
        )

        if features_df.empty:
            raise ValueError("No transaction data available for training")

        # Define churn labels: "churned" = no purchase within churn_threshold_days
        # of the dataset's most recent purchase. Anchoring on MAX(purchase_date)
        # instead of GETDATE() keeps both classes populated when the app runs
        # against a historical snapshot.
        churn_query = f"""
            SELECT hshd_num,
                   CASE WHEN MAX(purchase_date) < DATEADD(
                           day, {-churn_threshold_days},
                           (SELECT MAX(purchase_date) FROM transactions))
                   THEN 1 ELSE 0 END as churned
            FROM transactions
            GROUP BY hshd_num
        """

        result = await session.execute(text(churn_query))
        churn_data = pd.DataFrame(result.mappings().all())
        churn_data = churn_data.set_index("hshd_num")

        # Align features with targets
        common_idx = features_df.index.intersection(churn_data.index)
        X_aligned = features_df.loc[common_idx]
        y_aligned = churn_data.loc[common_idx, "churned"]

        if len(common_idx) < 10:
            raise ValueError(f"Insufficient training samples: {len(common_idx)}")

        # Prepare data
        X, y = prepare_training_data(X_aligned, y_aligned)
        self.feature_names = list(X_aligned.columns)

        # Train/test split (stratified for imbalanced churn)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        # Balance the classes. The 84.51° sample is mostly households that
        # keep shopping through 2020 — without sample weights GBT just learns
        # to always predict "not churned" because that minimises log-loss on
        # an imbalanced training set. compute_sample_weight("balanced") gives
        # each minority-class sample weight n_samples / (n_classes * count(y))
        # so both classes contribute equally to the loss.
        from sklearn.utils.class_weight import compute_sample_weight

        sample_weight = compute_sample_weight("balanced", y_train)

        # Train model
        self.model.fit(X_train, y_train, sample_weight=sample_weight)
        self.is_trained = True
        self.training_date = datetime.now()

        # Evaluate
        from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        # AUC (requires sklearn.metrics.roc_auc_score)
        from sklearn.metrics import roc_auc_score

        try:
            auc = roc_auc_score(y_test, y_pred_proba)
        except ValueError:
            auc = 0.0

        return {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "auc": float(auc),
            "training_date": self.training_date.isoformat(),
            "n_samples": len(common_idx),
            "n_features": X.shape[1],
        }

    async def predict(self, session: AsyncSession, hshd_num: int) -> dict:
        """
        Predict churn risk for a household.

        Returns:
            {
                "hshd_num": int,
                "churn_probability": float (0-1),
                "risk_level": str ("high" | "medium" | "low"),
                "is_churned": bool (probability > 0.5),
            }
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")

        # See clv_model.predict for the rationale: prepare_training_data
        # normalises against the input frame's max, so a single-row predict
        # collapses every feature to 1.0 and every household gets the same
        # prediction. Normalise across all households, then pluck the row.
        all_features = await get_churn_features(session)
        if all_features.empty or hshd_num not in all_features.index:
            raise ValueError(f"No transaction data for household {hshd_num}")

        feature_frame = (
            all_features[self.feature_names] if self.feature_names else all_features
        )
        all_X, _ = prepare_training_data(feature_frame)
        row_idx = all_features.index.get_loc(hshd_num)

        all_probs = self.model.predict_proba(all_X)[:, 1]
        churn_prob = float(all_probs[row_idx])

        # Percentile rank in [0, 100]: percent of households with a
        # churn_probability <= this one. The GBT's raw proba distribution
        # is bimodal on the 84.51° sample (~87% near 0, ~13% near 1) so
        # surfacing the percentile in the UI gives meaningful variety
        # across households even when the absolute proba is saturated.
        if len(all_probs) > 0:
            percentile = float(np.mean(all_probs <= churn_prob) * 100)
        else:
            percentile = 0.0

        # Risk tiers driven by percentile (matches CLV's segment shape).
        # is_churned still uses the raw proba so the binary classifier
        # decision stays available for callers that want it.
        if percentile >= 66:
            risk_level = "high"
        elif percentile >= 33:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "hshd_num": hshd_num,
            "churn_probability": churn_prob,
            "churn_percentile": percentile,
            "risk_level": risk_level,
            "is_churned": churn_prob > 0.5,
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
    def load(cls, data: bytes) -> "ChurnModel":
        """Deserialize model from bytes."""
        obj = pickle.loads(data)
        instance = cls(model=obj["model"])
        instance.feature_names = obj["feature_names"]
        instance.training_date = obj["training_date"]
        instance.is_trained = True
        return instance

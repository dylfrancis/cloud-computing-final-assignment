"""Model registry and management."""

from app.ml.basket_model import BasketModel
from app.ml.churn_model import ChurnModel
from app.ml.clv_model import CLVModel
from app.ml.persistence import load_model


class ModelRegistry:
    """In-memory registry for trained models.

    On construction, tries to load each model from the persistent artifact
    directory (``/home/ml-artifacts`` on Azure App Service). If no artifact
    is present, or if it's incompatible with the current code, falls back
    to a fresh untrained instance.
    """

    def __init__(self):
        self.clv_model = load_model("clv", CLVModel) or CLVModel()
        self.churn_model = load_model("churn", ChurnModel) or ChurnModel()
        self.basket_model = load_model("basket", BasketModel) or BasketModel()

    def get_clv(self) -> CLVModel:
        """Get CLV model."""
        return self.clv_model

    def get_churn(self) -> ChurnModel:
        """Get churn model."""
        return self.churn_model

    def get_basket(self) -> BasketModel:
        """Get basket model."""
        return self.basket_model

    def status(self) -> dict:
        """Get training status of all models."""
        return {
            "clv": {
                "trained": self.clv_model.is_trained,
                "training_date": self.clv_model.training_date.isoformat()
                if self.clv_model.training_date
                else None,
            },
            "churn": {
                "trained": self.churn_model.is_trained,
                "training_date": self.churn_model.training_date.isoformat()
                if self.churn_model.training_date
                else None,
            },
            "basket": {
                "trained": self.basket_model.associations is not None,
            },
        }


# Global registry instance
_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    """Get or create global model registry."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry

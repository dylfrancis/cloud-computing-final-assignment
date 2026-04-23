from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.ml.registry import get_registry

router = APIRouter(prefix="/ml", tags=["ml"])


# ==================== SCHEMAS ====================


class TrainingParams(BaseModel):
    """Parameters for model training."""

    lookback_days: int = 365
    future_days: int | None = None  # For CLV
    churn_threshold_days: int | None = None  # For churn
    min_support: float | None = None  # For basket


class CLVPrediction(BaseModel):
    """CLV prediction response."""

    hshd_num: int
    clv_score: float
    clv_percentile: float
    segment: str  # "high" | "medium" | "low"


class ChurnPrediction(BaseModel):
    """Churn prediction response."""

    hshd_num: int
    churn_probability: float
    risk_level: str  # "high" | "medium" | "low"
    is_churned: bool


class ProductRecommendation(BaseModel):
    """Single product recommendation."""

    product_id: int
    score: float
    reason: str


class BasketPrediction(BaseModel):
    """Basket analysis prediction response."""

    hshd_num: int
    recommendations: list[ProductRecommendation]


class TrainingResponse(BaseModel):
    """Response from training endpoint."""

    model: str
    status: str
    metrics: dict


class ModelStatus(BaseModel):
    """Status of a single model."""

    trained: bool
    training_date: str | None


class StatusResponse(BaseModel):
    """Response from status endpoint."""

    clv: ModelStatus
    churn: ModelStatus
    basket: dict


# ==================== ENDPOINTS ====================


@router.get("/status", response_model=StatusResponse)
async def get_model_status() -> StatusResponse:
    """Get training status of all ML models."""
    registry = get_registry()
    status = registry.status()

    return StatusResponse(
        clv=ModelStatus(**status["clv"]),
        churn=ModelStatus(**status["churn"]),
        basket=status["basket"],
    )


@router.post("/train/clv", response_model=TrainingResponse)
async def train_clv_model(
    params: TrainingParams, session: AsyncSession = Depends(get_db)
) -> TrainingResponse:
    """Train CLV prediction model."""
    try:
        registry = get_registry()
        model = registry.get_clv()

        metrics = await model.train(
            session,
            lookback_days=params.lookback_days,
            future_days=params.future_days or 90,
        )

        return TrainingResponse(
            model="clv",
            status="success",
            metrics=metrics,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Training failed: {str(e)}")


@router.post("/train/churn", response_model=TrainingResponse)
async def train_churn_model(
    params: TrainingParams, session: AsyncSession = Depends(get_db)
) -> TrainingResponse:
    """Train churn prediction model."""
    try:
        registry = get_registry()
        model = registry.get_churn()

        metrics = await model.train(
            session,
            lookback_days=params.lookback_days,
            churn_threshold_days=params.churn_threshold_days or 180,
        )

        return TrainingResponse(
            model="churn",
            status="success",
            metrics=metrics,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Training failed: {str(e)}")


@router.post("/train/basket", response_model=TrainingResponse)
async def train_basket_model(
    params: TrainingParams, session: AsyncSession = Depends(get_db)
) -> TrainingResponse:
    """Train market basket analysis model."""
    try:
        registry = get_registry()
        model = registry.get_basket()

        metrics = await model.train(
            session,
            lookback_days=params.lookback_days,
            min_support=params.min_support or 0.02,
        )

        return TrainingResponse(
            model="basket",
            status="success",
            metrics=metrics,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Training failed: {str(e)}")


@router.get("/predict/clv/{hshd_num}", response_model=CLVPrediction)
async def predict_clv(hshd_num: int, session: AsyncSession = Depends(get_db)) -> CLVPrediction:
    """Predict CLV for a household."""
    try:
        registry = get_registry()
        model = registry.get_clv()

        if not model.is_trained:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "CLV model not trained. Train it first with POST /ml/train/clv"
            )

        prediction = await model.predict(session, hshd_num)
        return CLVPrediction(**prediction)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Prediction failed: {str(e)}")


@router.get("/predict/churn/{hshd_num}", response_model=ChurnPrediction)
async def predict_churn(
    hshd_num: int, session: AsyncSession = Depends(get_db)
) -> ChurnPrediction:
    """Predict churn risk for a household."""
    try:
        registry = get_registry()
        model = registry.get_churn()

        if not model.is_trained:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Churn model not trained. Train it first with POST /ml/train/churn",
            )

        prediction = await model.predict(session, hshd_num)
        return ChurnPrediction(**prediction)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Prediction failed: {str(e)}")


@router.get("/predict/basket/{hshd_num}", response_model=BasketPrediction)
async def predict_basket(
    hshd_num: int, limit: int = 5, session: AsyncSession = Depends(get_db)
) -> BasketPrediction:
    """Get product recommendations for a household."""
    try:
        registry = get_registry()
        model = registry.get_basket()

        if model.associations is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Basket model not trained. Train it first with POST /ml/train/basket",
            )

        prediction = await model.predict(session, hshd_num, limit=limit)
        recs = [ProductRecommendation(**rec) for rec in prediction["recommendations"]]
        return BasketPrediction(hshd_num=hshd_num, recommendations=recs)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Prediction failed: {str(e)}")

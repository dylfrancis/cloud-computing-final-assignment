from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_email
from app.models.household import Household
from app.models.product import Product
from app.models.transaction import Transaction
from app.schemas.household import (
    HouseholdListResponse,
    HouseholdPullResponse,
    HouseholdSummary,
    PullRow,
)

router = APIRouter(
    prefix="/households",
    tags=["households"],
    dependencies=[Depends(get_current_user_email)],
)

PULL_SORT_COLS = (
    Transaction.hshd_num,
    Transaction.basket_num,
    Transaction.purchase_date,
    Transaction.product_num,
    Product.department,
    Product.commodity,
)


def _pull_select(hshd_num: int) -> Select:
    """Joined transactions ↔ products for one household, in the rubric's sort order."""
    return (
        select(
            Transaction.basket_num,
            Transaction.purchase_date,
            Transaction.product_num,
            Product.department,
            Product.commodity,
            Product.brand_type,
            Product.natural_organic_flag,
            Transaction.spend,
            Transaction.units,
            Transaction.store_region,
            Transaction.week_num,
            Transaction.year,
        )
        .join(Product, Product.product_num == Transaction.product_num)
        .where(Transaction.hshd_num == hshd_num)
        .order_by(*PULL_SORT_COLS)
    )


@router.get("", response_model=HouseholdListResponse)
async def list_households(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> HouseholdListResponse:
    total = await session.scalar(select(func.count()).select_from(Household))
    result = await session.execute(
        select(Household).order_by(Household.hshd_num).limit(limit).offset(offset)
    )
    households = [HouseholdSummary.model_validate(h) for h in result.scalars().all()]
    return HouseholdListResponse(total=int(total or 0), households=households)


@router.get("/{hshd_num}/pull", response_model=HouseholdPullResponse)
async def pull_household(
    hshd_num: int,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> HouseholdPullResponse:
    household = await session.get(Household, hshd_num)
    if household is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Household {hshd_num} not found")

    total = await session.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.hshd_num == hshd_num)
    )

    result = await session.execute(_pull_select(hshd_num).limit(limit).offset(offset))
    rows = [PullRow.model_validate(r, from_attributes=True) for r in result.mappings().all()]

    return HouseholdPullResponse(
        hshd_num=hshd_num,
        household=HouseholdSummary.model_validate(household),
        total_rows=int(total or 0),
        limit=limit,
        offset=offset,
        rows=rows,
    )

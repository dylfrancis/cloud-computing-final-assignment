"""Aggregate read-only endpoints feeding the dashboard page.

All series are all-time (no date range filter) — the rubric's demo flow is a
static snapshot of the 84.51° sample, and every one of these resolves to a
single ``GROUP BY`` on the ~900k transactions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, literal, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_email
from app.models.product import Product
from app.models.transaction import Transaction
from app.schemas.dashboard import (
    CategoryShare,
    CategoryShareList,
    DepartmentSpend,
    Kpis,
    SpendOverTime,
    SpendPoint,
    TopDepartments,
)

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user_email)],
)


@router.get("/kpis", response_model=Kpis)
async def kpis(session: AsyncSession = Depends(get_session)) -> Kpis:
    q = select(
        func.coalesce(func.sum(Transaction.spend), 0).label("total_spend"),
        func.coalesce(func.sum(Transaction.units), 0).label("total_units"),
        func.count(Transaction.id).label("transactions"),
        func.count(func.distinct(Transaction.hshd_num)).label("unique_households"),
        func.count(func.distinct(Transaction.product_num)).label("unique_products"),
        func.count(func.distinct(Transaction.basket_num)).label("unique_baskets"),
    )
    row = (await session.execute(q)).one()
    total_spend = float(row.total_spend or 0)
    baskets = int(row.unique_baskets or 0)
    return Kpis(
        total_spend=total_spend,
        total_units=int(row.total_units or 0),
        transactions=int(row.transactions or 0),
        unique_households=int(row.unique_households or 0),
        unique_products=int(row.unique_products or 0),
        unique_baskets=baskets,
        avg_basket_spend=(total_spend / baskets) if baskets else 0.0,
    )


def _bucket_expr(grain: str):
    """SQL Server: snap purchase_date to the start of its week (Monday) or
    month via DATEADD(DATEDIFF(...)). The datepart (``week``/``month``) must
    render as an unquoted identifier — ``literal_column`` gives us that;
    ``literal`` would emit it as a string and DATEDIFF rejects it."""
    unit = literal_column("week") if grain == "week" else literal_column("month")
    anchor = literal("1900-01-01")
    return func.dateadd(unit, func.datediff(unit, anchor, Transaction.purchase_date), anchor)


@router.get("/spend-over-time", response_model=SpendOverTime)
async def spend_over_time(
    grain: str = Query("week", pattern="^(week|month)$"),
    session: AsyncSession = Depends(get_session),
) -> SpendOverTime:
    bucket = _bucket_expr(grain)
    q = (
        select(
            bucket.label("bucket"),
            func.sum(Transaction.spend).label("spend"),
            func.count(Transaction.id).label("transactions"),
        )
        .group_by(bucket)
        .order_by(bucket)
    )
    rows = (await session.execute(q)).all()
    points = [
        SpendPoint(
            bucket=row.bucket.isoformat() if hasattr(row.bucket, "isoformat") else str(row.bucket),
            spend=float(row.spend or 0),
            transactions=int(row.transactions or 0),
        )
        for row in rows
    ]
    return SpendOverTime(grain=grain, points=points)


@router.get("/top-departments", response_model=TopDepartments)
async def top_departments(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> TopDepartments:
    q = (
        select(
            func.coalesce(Product.department, "UNKNOWN").label("department"),
            func.sum(Transaction.spend).label("spend"),
            func.count(Transaction.id).label("transactions"),
        )
        .join(Product, Product.product_num == Transaction.product_num)
        .group_by(Product.department)
        .order_by(func.sum(Transaction.spend).desc())
        .limit(limit)
    )
    rows = (await session.execute(q)).all()
    return TopDepartments(
        items=[
            DepartmentSpend(
                department=row.department,
                spend=float(row.spend or 0),
                transactions=int(row.transactions or 0),
            )
            for row in rows
        ]
    )


async def _category_share(session: AsyncSession, label_expr) -> CategoryShareList:
    q = (
        select(
            label_expr.label("label"),
            func.sum(Transaction.spend).label("spend"),
            func.count(Transaction.id).label("transactions"),
        )
        .join(Product, Product.product_num == Transaction.product_num)
        .group_by(label_expr)
        .order_by(func.sum(Transaction.spend).desc())
    )
    rows = (await session.execute(q)).all()
    total = float(sum(float(r.spend or 0) for r in rows))
    return CategoryShareList(
        total_spend=total,
        items=[
            CategoryShare(
                label=row.label,
                spend=float(row.spend or 0),
                transactions=int(row.transactions or 0),
                share=(float(row.spend or 0) / total) if total else 0.0,
            )
            for row in rows
        ],
    )


@router.get("/brand-mix", response_model=CategoryShareList)
async def brand_mix(session: AsyncSession = Depends(get_session)) -> CategoryShareList:
    return await _category_share(session, func.coalesce(Product.brand_type, "UNKNOWN"))


@router.get("/organic-mix", response_model=CategoryShareList)
async def organic_mix(session: AsyncSession = Depends(get_session)) -> CategoryShareList:
    labeled = case(
        (Product.natural_organic_flag == "Y", "Natural/Organic"),
        (Product.natural_organic_flag == "N", "Conventional"),
        else_="UNKNOWN",
    )
    return await _category_share(session, labeled)

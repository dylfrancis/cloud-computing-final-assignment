from pydantic import BaseModel


class Kpis(BaseModel):
    total_spend: float
    total_units: int
    transactions: int
    unique_households: int
    unique_products: int
    unique_baskets: int
    avg_basket_spend: float


class SpendPoint(BaseModel):
    bucket: str  # ISO date of the week/month start
    spend: float
    transactions: int


class SpendOverTime(BaseModel):
    grain: str  # "week" | "month"
    points: list[SpendPoint]


class CategoryShare(BaseModel):
    label: str
    spend: float
    transactions: int
    share: float  # 0..1


class CategoryShareList(BaseModel):
    total_spend: float
    items: list[CategoryShare]


class DepartmentSpend(BaseModel):
    department: str
    spend: float
    transactions: int


class TopDepartments(BaseModel):
    items: list[DepartmentSpend]

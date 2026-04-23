from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class HouseholdSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hshd_num: int
    loyalty_flag: str | None = None
    age_range: str | None = None
    marital_status: str | None = None
    income_range: str | None = None
    homeowner_desc: str | None = None
    household_composition: str | None = None
    household_size: str | None = None
    children: str | None = None


class PullRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    basket_num: int
    purchase_date: date
    product_num: int
    department: str | None = None
    commodity: str | None = None
    brand_type: str | None = None
    natural_organic_flag: str | None = None
    spend: float
    units: int
    store_region: str | None = None
    week_num: int | None = None
    year: int | None = None


class HouseholdPullResponse(BaseModel):
    hshd_num: int
    household: HouseholdSummary
    total_rows: int
    limit: int
    offset: int
    rows: list[PullRow]


class HouseholdListResponse(BaseModel):
    total: int
    households: list[HouseholdSummary] = Field(default_factory=list)

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Household(Base):
    __tablename__ = "households"

    hshd_num: Mapped[int] = mapped_column(Integer, primary_key=True)
    loyalty_flag: Mapped[str | None] = mapped_column(String(1), nullable=True)
    age_range: Mapped[str | None] = mapped_column(String(20), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    income_range: Mapped[str | None] = mapped_column(String(30), nullable=True)
    homeowner_desc: Mapped[str | None] = mapped_column(String(30), nullable=True)
    household_composition: Mapped[str | None] = mapped_column(String(30), nullable=True)
    household_size: Mapped[str | None] = mapped_column(String(10), nullable=True)
    children: Mapped[str | None] = mapped_column(String(10), nullable=True)

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    hshd_num: Mapped[int] = mapped_column(ForeignKey("households.hshd_num"), index=True)
    basket_num: Mapped[int] = mapped_column(Integer, index=True)
    purchase_date: Mapped[date] = mapped_column(Date, index=True)
    product_num: Mapped[int] = mapped_column(ForeignKey("products.product_num"), index=True)
    spend: Mapped[float] = mapped_column(Numeric(10, 2))
    units: Mapped[int] = mapped_column(Integer)
    store_region: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    week_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)

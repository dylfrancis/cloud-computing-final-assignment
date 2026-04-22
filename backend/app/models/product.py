from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Product(Base):
    __tablename__ = "products"

    product_num: Mapped[int] = mapped_column(Integer, primary_key=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    commodity: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    brand_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    natural_organic_flag: Mapped[str | None] = mapped_column(String(1), nullable=True)

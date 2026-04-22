"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "households",
        sa.Column("hshd_num", sa.Integer(), primary_key=True),
        sa.Column("loyalty_flag", sa.String(1), nullable=True),
        sa.Column("age_range", sa.String(20), nullable=True),
        sa.Column("marital_status", sa.String(20), nullable=True),
        sa.Column("income_range", sa.String(30), nullable=True),
        sa.Column("homeowner_desc", sa.String(30), nullable=True),
        sa.Column("household_composition", sa.String(30), nullable=True),
        sa.Column("household_size", sa.String(10), nullable=True),
        sa.Column("children", sa.String(10), nullable=True),
    )

    op.create_table(
        "products",
        sa.Column("product_num", sa.Integer(), primary_key=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("commodity", sa.String(100), nullable=True),
        sa.Column("brand_type", sa.String(30), nullable=True),
        sa.Column("natural_organic_flag", sa.String(1), nullable=True),
    )
    op.create_index("ix_products_department", "products", ["department"])
    op.create_index("ix_products_commodity", "products", ["commodity"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hshd_num", sa.Integer(), sa.ForeignKey("households.hshd_num"), nullable=False),
        sa.Column("basket_num", sa.Integer(), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("product_num", sa.Integer(), sa.ForeignKey("products.product_num"), nullable=False),
        sa.Column("spend", sa.Numeric(10, 2), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("store_region", sa.String(30), nullable=True),
        sa.Column("week_num", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
    )
    op.create_index("ix_transactions_hshd_num", "transactions", ["hshd_num"])
    op.create_index("ix_transactions_basket_num", "transactions", ["basket_num"])
    op.create_index("ix_transactions_purchase_date", "transactions", ["purchase_date"])
    op.create_index("ix_transactions_product_num", "transactions", ["product_num"])
    op.create_index("ix_transactions_store_region", "transactions", ["store_region"])


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("products")
    op.drop_table("households")
    op.drop_table("users")

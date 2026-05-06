"""delivery orders and operators

Revision ID: 20260506_0002
Revises: 20260504_0001
Create Date: 2026-05-06 23:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "20260506_0002"
down_revision = "20260504_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("phone_whatsapp", sa.String(length=32), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_whatsapp", name="uq_customers_phone_whatsapp"),
    )
    op.create_table(
        "restaurant_branches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("qr_code_image", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_restaurant_branches_restaurant", "restaurant_branches", ["restaurant_id"], unique=False)
    op.create_table(
        "operators",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("avatar", sa.String(length=255), nullable=True),
        sa.Column("login", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("position", sa.String(length=120), server_default="Оператор", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["restaurant_branches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("login", name="uq_operators_login"),
    )
    op.create_index("idx_operators_restaurant", "operators", ["restaurant_id"], unique=False)
    op.create_index("idx_operators_branch", "operators", ["branch_id"], unique=False)
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_number", sa.String(length=32), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("status", mysql.ENUM("new", "accepted", "courier", "completed", "cancelled"), server_default="new", nullable=False),
        sa.Column("payment_type", mysql.ENUM("cash", "online"), server_default="online", nullable=False),
        sa.Column("payment_status", mysql.ENUM("pending", "receipt_uploaded", "paid"), server_default="pending", nullable=False),
        sa.Column("delivery_address", sa.String(length=255), nullable=False),
        sa.Column("customer_comment", sa.Text(), nullable=True),
        sa.Column("yandex_delivery_url", sa.String(length=500), nullable=True),
        sa.Column("delivery_fee", sa.Integer(), server_default="0", nullable=False),
        sa.Column("receipt_image", sa.String(length=255), nullable=True),
        sa.Column("subtotal_amount", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["restaurant_branches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number", name="uq_orders_order_number"),
    )
    op.create_index("idx_orders_restaurant", "orders", ["restaurant_id"], unique=False)
    op.create_index("idx_orders_branch", "orders", ["branch_id"], unique=False)
    op.create_index("idx_orders_customer", "orders", ["customer_id"], unique=False)
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=True),
        sa.Column("item_name", sa.String(length=200), nullable=False),
        sa.Column("item_price", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("amount_label", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_order_items_order", "order_items", ["order_id"], unique=False)
    op.create_index("idx_order_items_menu_item", "order_items", ["menu_item_id"], unique=False)


def downgrade():
    op.drop_index("idx_order_items_menu_item", table_name="order_items")
    op.drop_index("idx_order_items_order", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("idx_orders_customer", table_name="orders")
    op.drop_index("idx_orders_branch", table_name="orders")
    op.drop_index("idx_orders_restaurant", table_name="orders")
    op.drop_table("orders")
    op.drop_index("idx_operators_branch", table_name="operators")
    op.drop_index("idx_operators_restaurant", table_name="operators")
    op.drop_table("operators")
    op.drop_index("idx_restaurant_branches_restaurant", table_name="restaurant_branches")
    op.drop_table("restaurant_branches")
    op.drop_table("customers")

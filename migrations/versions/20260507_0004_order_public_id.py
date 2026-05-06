"""add order public id

Revision ID: 20260507_0004
Revises: 20260507_0003
Create Date: 2026-05-07 02:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260507_0004"
down_revision = "20260507_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "orders",
        sa.Column("public_id", sa.String(length=64), nullable=True),
    )
    op.create_index("idx_orders_public_id", "orders", ["public_id"], unique=True)

    bind = op.get_bind()
    existing = bind.execute(sa.text("SELECT id FROM orders WHERE public_id IS NULL OR public_id = ''")).fetchall()
    for (order_id,) in existing:
        bind.execute(
            sa.text("UPDATE orders SET public_id = :pid WHERE id = :id"),
            {"pid": __generate_public_id(order_id), "id": order_id},
        )

    op.alter_column("orders", "public_id", existing_type=sa.String(length=64), nullable=False)


def downgrade():
    op.drop_index("idx_orders_public_id", table_name="orders")
    op.drop_column("orders", "public_id")


def __generate_public_id(order_id):
    import uuid

    return f"{order_id}-{uuid.uuid4().hex}"[:64]

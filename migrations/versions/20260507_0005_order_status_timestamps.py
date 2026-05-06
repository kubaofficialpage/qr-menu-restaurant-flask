"""add order status timestamps

Revision ID: 20260507_0005
Revises: 20260507_0004
Create Date: 2026-05-07 03:05:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260507_0005"
down_revision = "20260507_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("accepted_at", sa.DateTime(), nullable=True))
    op.add_column("orders", sa.Column("courier_handed_at", sa.DateTime(), nullable=True))
    op.add_column("orders", sa.Column("customer_completed_at", sa.DateTime(), nullable=True))
    op.add_column("orders", sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.add_column("orders", sa.Column("cancelled_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("orders", "cancelled_at")
    op.drop_column("orders", "completed_at")
    op.drop_column("orders", "customer_completed_at")
    op.drop_column("orders", "courier_handed_at")
    op.drop_column("orders", "accepted_at")

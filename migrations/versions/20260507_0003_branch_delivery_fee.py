"""add branch delivery fee

Revision ID: 20260507_0003
Revises: 20260506_0002
Create Date: 2026-05-07 01:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260507_0003"
down_revision = "20260506_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "restaurant_branches",
        sa.Column("delivery_fee", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade():
    op.drop_column("restaurant_branches", "delivery_fee")

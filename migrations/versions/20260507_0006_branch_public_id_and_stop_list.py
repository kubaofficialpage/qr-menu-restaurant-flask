"""add branch public id and stop list table

Revision ID: 20260507_0006
Revises: 20260507_0005
Create Date: 2026-05-07 03:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260507_0006"
down_revision = "20260507_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "restaurant_branches",
        sa.Column("public_id", sa.String(length=64), nullable=True),
    )
    op.create_index("idx_restaurant_branches_public_id", "restaurant_branches", ["public_id"], unique=True)

    bind = op.get_bind()
    existing = bind.execute(sa.text("SELECT id FROM restaurant_branches WHERE public_id IS NULL OR public_id = ''")).fetchall()
    for (branch_id,) in existing:
        bind.execute(
            sa.text("UPDATE restaurant_branches SET public_id = :pid WHERE id = :id"),
            {"pid": _generate_public_id(branch_id), "id": branch_id},
        )

    op.alter_column("restaurant_branches", "public_id", existing_type=sa.String(length=64), nullable=False)

    op.create_table(
        "branch_stop_list_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["restaurant_branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("branch_id", "menu_item_id", name="uq_branch_stop_list_branch_item"),
    )
    op.create_index("ix_branch_stop_list_items_branch_id", "branch_stop_list_items", ["branch_id"], unique=False)
    op.create_index("ix_branch_stop_list_items_menu_item_id", "branch_stop_list_items", ["menu_item_id"], unique=False)


def downgrade():
    op.drop_index("ix_branch_stop_list_items_menu_item_id", table_name="branch_stop_list_items")
    op.drop_index("ix_branch_stop_list_items_branch_id", table_name="branch_stop_list_items")
    op.drop_table("branch_stop_list_items")

    op.drop_index("idx_restaurant_branches_public_id", table_name="restaurant_branches")
    op.drop_column("restaurant_branches", "public_id")


def _generate_public_id(branch_id):
    import uuid

    return f"branch-{branch_id}-{uuid.uuid4().hex}"[:64]

"""initial schema

Revision ID: 20260504_0001
Revises: None
Create Date: 2026-05-04 00:00:01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = "20260504_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=190), nullable=False),
        sa.Column("avatar", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("global_role", mysql.ENUM("developer", "user"), server_default="user", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "restaurants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("classic_info", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=190), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("logo", sa.String(length=255), nullable=True),
        sa.Column("work_hours", sa.Text(), nullable=True),
        sa.Column("admin_contact", sa.String(length=255), nullable=True),
        sa.Column("director_contact", sa.String(length=255), nullable=True),
        sa.Column("opening_date", sa.Date(), nullable=True),
        sa.Column("support_phone", sa.String(length=50), nullable=True),
        sa.Column("support_email", sa.String(length=190), nullable=True),
        sa.Column("map_2gis_url", sa.String(length=500), nullable=True),
        sa.Column("map_2gis_embed_url", sa.String(length=500), nullable=True),
        sa.Column("currency", sa.String(length=10), server_default="KZT", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_restaurants_created_by", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_restaurants_slug"),
    )
    op.create_index("idx_restaurants_active", "restaurants", ["is_active"], unique=False)
    op.create_table(
        "restaurant_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", mysql.ENUM("restaurant_admin"), server_default="restaurant_admin", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], name="fk_restaurant_users_restaurant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_restaurant_users_user", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurant_id", "user_id", name="uq_restaurant_users_restaurant_user"),
    )
    op.create_index("idx_restaurant_users_user", "restaurant_users", ["user_id"], unique=False)
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], name="fk_categories_restaurant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurant_id", "name", name="uq_categories_restaurant_name"),
    )
    op.create_index("idx_categories_restaurant", "categories", ["restaurant_id"], unique=False)
    op.create_table(
        "menu",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ingredients", sa.Text(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("amount", sa.String(length=50), nullable=True),
        sa.Column("image", sa.String(length=255), nullable=True),
        sa.Column("is_available", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name="fk_menu_category", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], name="fk_menu_restaurant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurant_id", "name", name="uq_menu_restaurant_name"),
    )
    op.create_index("idx_menu_restaurant", "menu", ["restaurant_id"], unique=False)
    op.create_index("idx_menu_category", "menu", ["category_id"], unique=False)
    op.create_table(
        "restaurant_settings",
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("theme_color", sa.String(length=20), nullable=True),
        sa.Column("language", sa.String(length=10), server_default="ru", nullable=False),
        sa.Column("service_fee_percent", sa.Numeric(precision=5, scale=2), server_default="0.00", nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], name="fk_restaurant_settings_restaurant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("restaurant_id"),
    )
    op.create_table(
        "restaurant_visit_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("page_path", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], name="fk_visit_events_restaurant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_visit_restaurant_created", "restaurant_visit_events", ["restaurant_id", "created_at"], unique=False)
    op.create_index("idx_visit_session", "restaurant_visit_events", ["session_id"], unique=False)
    op.create_table(
        "menu_cart_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu.id"], name="fk_cart_events_menu_item", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], name="fk_cart_events_restaurant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cart_events_restaurant_created", "menu_cart_events", ["restaurant_id", "created_at"], unique=False)
    op.create_index("idx_cart_events_menu_item", "menu_cart_events", ["menu_item_id"], unique=False)
    op.create_index("idx_cart_events_session", "menu_cart_events", ["session_id"], unique=False)


def downgrade():
    op.drop_index("idx_cart_events_session", table_name="menu_cart_events")
    op.drop_index("idx_cart_events_menu_item", table_name="menu_cart_events")
    op.drop_index("idx_cart_events_restaurant_created", table_name="menu_cart_events")
    op.drop_table("menu_cart_events")
    op.drop_index("idx_visit_session", table_name="restaurant_visit_events")
    op.drop_index("idx_visit_restaurant_created", table_name="restaurant_visit_events")
    op.drop_table("restaurant_visit_events")
    op.drop_table("restaurant_settings")
    op.drop_index("idx_menu_category", table_name="menu")
    op.drop_index("idx_menu_restaurant", table_name="menu")
    op.drop_table("menu")
    op.drop_index("idx_categories_restaurant", table_name="categories")
    op.drop_table("categories")
    op.drop_index("idx_restaurant_users_user", table_name="restaurant_users")
    op.drop_table("restaurant_users")
    op.drop_index("idx_restaurants_active", table_name="restaurants")
    op.drop_table("restaurants")
    op.drop_table("users")

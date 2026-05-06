from sqlalchemy import func
from sqlalchemy.dialects.mysql import ENUM

from database.extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), nullable=False, unique=True)
    avatar = db.Column(db.String(255))
    password_hash = db.Column(db.String(255), nullable=False)
    global_role = db.Column(ENUM("developer", "user"), nullable=False, server_default="user")
    is_active = db.Column(db.Boolean, nullable=False, server_default=db.true())

    created_restaurants = db.relationship("Restaurant", back_populates="creator")
    restaurant_links = db.relationship("RestaurantUser", back_populates="user", cascade="all, delete-orphan")


class Restaurant(TimestampMixin, db.Model):
    __tablename__ = "restaurants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text)
    classic_info = db.Column(db.Text)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(190))
    address = db.Column(db.String(255))
    logo = db.Column(db.String(255))
    work_hours = db.Column(db.Text)
    admin_contact = db.Column(db.String(255))
    director_contact = db.Column(db.String(255))
    opening_date = db.Column(db.Date)
    support_phone = db.Column(db.String(50))
    support_email = db.Column(db.String(190))
    map_2gis_url = db.Column(db.String(500))
    map_2gis_embed_url = db.Column(db.String(500))
    currency = db.Column(db.String(10), nullable=False, server_default="KZT")
    is_active = db.Column(db.Boolean, nullable=False, server_default=db.true())
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))

    creator = db.relationship("User", back_populates="created_restaurants")
    members = db.relationship("RestaurantUser", back_populates="restaurant", cascade="all, delete-orphan")
    categories = db.relationship("Category", back_populates="restaurant", cascade="all, delete-orphan")
    menu_items = db.relationship("MenuItem", back_populates="restaurant", cascade="all, delete-orphan")
    settings = db.relationship("RestaurantSetting", back_populates="restaurant", uselist=False, cascade="all, delete-orphan")
    visit_events = db.relationship("RestaurantVisitEvent", back_populates="restaurant", cascade="all, delete-orphan")
    cart_events = db.relationship("MenuCartEvent", back_populates="restaurant", cascade="all, delete-orphan")


class RestaurantUser(db.Model):
    __tablename__ = "restaurant_users"
    __table_args__ = (
        db.UniqueConstraint("restaurant_id", "user_id", name="uq_restaurant_users_restaurant_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = db.Column(ENUM("restaurant_admin"), nullable=False, server_default="restaurant_admin")
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())

    restaurant = db.relationship("Restaurant", back_populates="members")
    user = db.relationship("User", back_populates="restaurant_links")


class Category(TimestampMixin, db.Model):
    __tablename__ = "categories"
    __table_args__ = (
        db.UniqueConstraint("restaurant_id", "name", name="uq_categories_restaurant_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, server_default="0")
    is_active = db.Column(db.Boolean, nullable=False, server_default=db.true())

    restaurant = db.relationship("Restaurant", back_populates="categories")
    menu_items = db.relationship("MenuItem", back_populates="category")


class MenuItem(TimestampMixin, db.Model):
    __tablename__ = "menu"
    __table_args__ = (
        db.UniqueConstraint("restaurant_id", "name", name="uq_menu_restaurant_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    ingredients = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.String(50))
    image = db.Column(db.String(255))
    is_available = db.Column(db.Boolean, nullable=False, server_default=db.true())
    sort_order = db.Column(db.Integer, nullable=False, server_default="0")

    restaurant = db.relationship("Restaurant", back_populates="menu_items")
    category = db.relationship("Category", back_populates="menu_items")
    cart_events = db.relationship("MenuCartEvent", back_populates="menu_item", cascade="all, delete-orphan")


class RestaurantSetting(db.Model):
    __tablename__ = "restaurant_settings"

    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), primary_key=True)
    theme_color = db.Column(db.String(20))
    language = db.Column(db.String(10), nullable=False, server_default="ru")
    service_fee_percent = db.Column(db.Numeric(5, 2), nullable=False, server_default="0.00")
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )

    restaurant = db.relationship("Restaurant", back_populates="settings")


class RestaurantVisitEvent(db.Model):
    __tablename__ = "restaurant_visit_events"

    id = db.Column(db.BigInteger, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    page_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())

    restaurant = db.relationship("Restaurant", back_populates="visit_events")


class MenuCartEvent(db.Model):
    __tablename__ = "menu_cart_events"

    id = db.Column(db.BigInteger, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    quantity_delta = db.Column(db.Integer, nullable=False, server_default="1")
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())

    restaurant = db.relationship("Restaurant", back_populates="cart_events")
    menu_item = db.relationship("MenuItem", back_populates="cart_events")


class RestaurantBranch(TimestampMixin, db.Model):
    __tablename__ = "restaurant_branches"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    delivery_fee = db.Column(db.Integer, nullable=False, server_default="0")
    qr_code_image = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, server_default=db.true())

    restaurant = db.relationship("Restaurant", backref=db.backref("branches", cascade="all, delete-orphan"))
    operators = db.relationship("Operator", back_populates="branch", cascade="all, delete-orphan")
    orders = db.relationship("Order", back_populates="branch")


class Operator(TimestampMixin, db.Model):
    __tablename__ = "operators"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("restaurant_branches.id", ondelete="SET NULL"), index=True)
    full_name = db.Column(db.String(160), nullable=False)
    avatar = db.Column(db.String(255))
    login = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    position = db.Column(db.String(120), nullable=False, server_default="Оператор")
    is_active = db.Column(db.Boolean, nullable=False, server_default=db.true())

    restaurant = db.relationship("Restaurant", backref=db.backref("operators", cascade="all, delete-orphan"))
    branch = db.relationship("RestaurantBranch", back_populates="operators")


class Customer(TimestampMixin, db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(160), nullable=False)
    phone_whatsapp = db.Column(db.String(32), nullable=False, unique=True)
    address = db.Column(db.String(255))

    orders = db.relationship("Order", back_populates="customer")


class Order(TimestampMixin, db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(32), nullable=False, unique=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("restaurant_branches.id", ondelete="SET NULL"), index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="SET NULL"), index=True)
    status = db.Column(
        ENUM("new", "accepted", "courier", "completed", "cancelled"),
        nullable=False,
        server_default="new",
    )
    payment_type = db.Column(ENUM("cash", "online"), nullable=False, server_default="online")
    payment_status = db.Column(
        ENUM("pending", "receipt_uploaded", "paid"),
        nullable=False,
        server_default="pending",
    )
    delivery_address = db.Column(db.String(255), nullable=False)
    customer_comment = db.Column(db.Text)
    yandex_delivery_url = db.Column(db.String(500))
    delivery_fee = db.Column(db.Integer, nullable=False, server_default="0")
    receipt_image = db.Column(db.String(255))
    subtotal_amount = db.Column(db.Integer, nullable=False, server_default="0")
    total_amount = db.Column(db.Integer, nullable=False, server_default="0")

    restaurant = db.relationship("Restaurant", backref=db.backref("orders", cascade="all, delete-orphan"))
    branch = db.relationship("RestaurantBranch", back_populates="orders")
    customer = db.relationship("Customer", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu.id", ondelete="SET NULL"), index=True)
    item_name = db.Column(db.String(200), nullable=False)
    item_price = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, server_default="1")
    amount_label = db.Column(db.String(50))

    order = db.relationship("Order", back_populates="items")
    menu_item = db.relationship("MenuItem")

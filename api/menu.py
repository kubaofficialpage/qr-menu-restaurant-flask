from flask import Blueprint, jsonify, request, session
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database.analytics import get_or_create_analytics_session, record_menu_cart_add
from database.db import get_session
from database.models import BranchStopListItem, Category, MenuItem, Restaurant, RestaurantBranch

menu_api = Blueprint("menu_api", __name__)


def model_to_dict(model, extra=None):
    data = {column.name: getattr(model, column.name) for column in model.__table__.columns}
    if extra:
        data.update(extra)
    return data


def serialize_restaurant(restaurant):
    creator = restaurant.creator
    return model_to_dict(
        restaurant,
        extra={
            "creator_name": creator.name if creator else None,
            "creator_email": creator.email if creator else None,
            "creator_avatar": creator.avatar if creator else None,
        },
    )


def serialize_menu_item(menu_item):
    return model_to_dict(menu_item)


def serialize_category(category):
    return model_to_dict(category)


def get_restaurant_by_slug(slug):
    db_session = get_session()
    restaurant = db_session.execute(
        select(Restaurant)
        .options(joinedload(Restaurant.creator))
        .where(Restaurant.slug == slug, Restaurant.is_active.is_(True))
    ).scalar_one_or_none()
    return serialize_restaurant(restaurant) if restaurant else None


def get_restaurant_by_slug_any_status(slug):
    db_session = get_session()
    restaurant = db_session.execute(
        select(Restaurant)
        .options(joinedload(Restaurant.creator))
        .where(Restaurant.slug == slug)
    ).scalar_one_or_none()
    return serialize_restaurant(restaurant) if restaurant else None


def get_default_restaurant():
    db_session = get_session()
    restaurant = db_session.execute(
        select(Restaurant)
        .options(joinedload(Restaurant.creator))
        .where(Restaurant.is_active.is_(True))
        .order_by(Restaurant.id)
        .limit(1)
    ).scalar_one_or_none()
    return serialize_restaurant(restaurant) if restaurant else None


def get_active_restaurants():
    db_session = get_session()
    restaurants = db_session.execute(
        select(Restaurant)
        .where(Restaurant.is_active.is_(True))
        .order_by(Restaurant.name)
    ).scalars().all()
    return [
        {
            "id": restaurant.id,
            "name": restaurant.name,
            "slug": restaurant.slug,
            "logo": restaurant.logo,
            "address": restaurant.address,
            "description": restaurant.description,
        }
        for restaurant in restaurants
    ]


def get_restaurant_menu(restaurant_id):
    db_session = get_session()
    menu = db_session.execute(
        select(MenuItem)
        .where(MenuItem.restaurant_id == restaurant_id)
        .order_by(MenuItem.sort_order, MenuItem.name)
    ).scalars().all()
    categories = db_session.execute(
        select(Category)
        .where(Category.restaurant_id == restaurant_id, Category.is_active.is_(True))
        .order_by(Category.sort_order, Category.name)
    ).scalars().all()
    return menu, categories


def get_branch_by_public_id(restaurant_id, branch_public_id):
    db_session = get_session()
    return db_session.execute(
        select(RestaurantBranch).where(
            RestaurantBranch.restaurant_id == restaurant_id,
            RestaurantBranch.public_id == branch_public_id,
            RestaurantBranch.is_active.is_(True),
        )
    ).scalar_one_or_none()


def get_branch_stop_list_ids(branch_id):
    db_session = get_session()
    rows = db_session.execute(
        select(BranchStopListItem.menu_item_id).where(BranchStopListItem.branch_id == branch_id)
    ).scalars().all()
    return set(rows)


@menu_api.route("/api/menu")
def get_menu():
    restaurant = get_default_restaurant()
    if not restaurant:
        return jsonify({"restaurant": None, "menu": [], "categories": []})

    menu, categories = get_restaurant_menu(restaurant["id"])
    return jsonify(
        {
            "restaurant": restaurant,
            "menu": [serialize_menu_item(item) for item in menu],
            "categories": [serialize_category(category) for category in categories],
        }
    )


@menu_api.route("/api/<restaurant_slug>/menu")
def get_menu_by_restaurant(restaurant_slug):
    restaurant = get_restaurant_by_slug(restaurant_slug)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    menu, categories = get_restaurant_menu(restaurant["id"])
    return jsonify(
        {
            "restaurant": restaurant,
            "menu": [serialize_menu_item(item) for item in menu],
            "categories": [serialize_category(category) for category in categories],
        }
    )


@menu_api.route("/api/<restaurant_slug>/<branch_public_id>/menu")
def get_menu_by_restaurant_branch(restaurant_slug, branch_public_id):
    restaurant = get_restaurant_by_slug(restaurant_slug)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    branch = get_branch_by_public_id(restaurant["id"], branch_public_id)
    if not branch:
        return jsonify({"error": "Branch not found"}), 404

    menu, categories = get_restaurant_menu(restaurant["id"])
    stop_list_ids = get_branch_stop_list_ids(branch.id)

    serialized_menu = []
    for item in menu:
        item_data = serialize_menu_item(item)
        if item.id in stop_list_ids:
            item_data["is_available"] = False
        serialized_menu.append(item_data)

    branch_data = {
        "id": branch.id,
        "public_id": branch.public_id,
        "name": branch.name,
        "address": branch.address,
        "delivery_fee": branch.delivery_fee,
        "qr_code_image": branch.qr_code_image,
        "qr_code_url": f"/static/resource/{branch.qr_code_image}" if branch.qr_code_image else None,
        "is_active": branch.is_active,
    }

    return jsonify(
        {
            "restaurant": restaurant,
            "branch": branch_data,
            "menu": serialized_menu,
            "categories": [serialize_category(category) for category in categories],
        }
    )


@menu_api.route("/api/analytics/cart-add", methods=["POST"])
def track_cart_add():
    payload = request.get_json(silent=True) or {}
    restaurant_id = payload.get("restaurantId")
    menu_item_id = payload.get("menuItemId")
    quantity_delta = payload.get("quantityDelta", 1)

    try:
        restaurant_id = int(restaurant_id)
        menu_item_id = int(menu_item_id)
        quantity_delta = int(quantity_delta)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "Invalid analytics payload."}), 400

    if quantity_delta <= 0:
        return jsonify({"ok": False, "message": "Quantity delta must be positive."}), 400

    menu_item = fetch_menu_item_restaurant(menu_item_id)
    if not menu_item or menu_item["restaurant_id"] != restaurant_id:
        return jsonify({"ok": False, "message": "Menu item not found."}), 404

    session_id = get_or_create_analytics_session(session)
    record_menu_cart_add(restaurant_id, menu_item_id, session_id, quantity_delta)
    return jsonify({"ok": True}), 201


def fetch_menu_item_restaurant(menu_item_id):
    db_session = get_session()
    item = db_session.execute(
        select(MenuItem.id, MenuItem.restaurant_id).where(MenuItem.id == menu_item_id)
    ).mappings().first()
    return dict(item) if item else None

from flask import Blueprint, jsonify, request, session

from database.analytics import get_or_create_analytics_session, record_menu_cart_add

from database.db import get_db

menu_api = Blueprint("menu_api", __name__)


def get_restaurant_by_slug(slug):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT r.*, u.name AS creator_name, u.email AS creator_email, u.avatar AS creator_avatar
        FROM restaurants r
        LEFT JOIN users u ON u.id = r.created_by
        WHERE r.slug = %s AND r.is_active = TRUE
        """,
        (slug,),
    )
    restaurant = cursor.fetchone()
    cursor.close()
    conn.close()
    return restaurant


def get_restaurant_by_slug_any_status(slug):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT r.*, u.name AS creator_name, u.email AS creator_email, u.avatar AS creator_avatar
        FROM restaurants r
        LEFT JOIN users u ON u.id = r.created_by
        WHERE r.slug = %s
        """,
        (slug,),
    )
    restaurant = cursor.fetchone()
    cursor.close()
    conn.close()
    return restaurant


def get_default_restaurant():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT r.*, u.name AS creator_name, u.email AS creator_email, u.avatar AS creator_avatar
        FROM restaurants r
        LEFT JOIN users u ON u.id = r.created_by
        WHERE r.is_active = TRUE
        ORDER BY r.id
        LIMIT 1
        """
    )
    restaurant = cursor.fetchone()
    cursor.close()
    conn.close()
    return restaurant


def get_active_restaurants():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, name, slug, logo, address, description
        FROM restaurants
        WHERE is_active = TRUE
        ORDER BY name
        """
    )
    restaurants = cursor.fetchall()
    cursor.close()
    conn.close()
    return restaurants


def get_restaurant_menu(restaurant_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM menu
        WHERE restaurant_id = %s
        ORDER BY sort_order, name
        """,
        (restaurant_id,),
    )
    menu = cursor.fetchall()

    cursor.execute(
        """
        SELECT *
        FROM categories
        WHERE restaurant_id = %s AND is_active = TRUE
        ORDER BY sort_order, name
        """,
        (restaurant_id,),
    )
    categories = cursor.fetchall()

    cursor.close()
    conn.close()
    return menu, categories


@menu_api.route("/api/menu")
def get_menu():
    restaurant = get_default_restaurant()
    if not restaurant:
        return jsonify({"restaurant": None, "menu": [], "categories": []})

    menu, categories = get_restaurant_menu(restaurant["id"])
    return jsonify({"restaurant": restaurant, "menu": menu, "categories": categories})


@menu_api.route("/api/<restaurant_slug>/menu")
def get_menu_by_restaurant(restaurant_slug):
    restaurant = get_restaurant_by_slug(restaurant_slug)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    menu, categories = get_restaurant_menu(restaurant["id"])
    return jsonify({"restaurant": restaurant, "menu": menu, "categories": categories})


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
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, restaurant_id FROM menu WHERE id = %s",
        (menu_item_id,),
    )
    item = cursor.fetchone()
    cursor.close()
    conn.close()
    return item

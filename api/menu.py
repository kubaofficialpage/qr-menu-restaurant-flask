from flask import Blueprint, jsonify

from database.db import get_db

menu_api = Blueprint("menu_api", __name__)


def get_restaurant_by_slug(slug):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM restaurants WHERE slug = %s AND is_active = TRUE",
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
        "SELECT * FROM restaurants WHERE slug = %s",
        (slug,),
    )
    restaurant = cursor.fetchone()
    cursor.close()
    conn.close()
    return restaurant


def get_default_restaurant():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM restaurants WHERE is_active = TRUE ORDER BY id LIMIT 1")
    restaurant = cursor.fetchone()
    cursor.close()
    conn.close()
    return restaurant


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

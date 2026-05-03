from flask import flash, request, session
from sqlalchemy import func, select

from database.db import get_session
from database.models import Category, MenuItem, Restaurant, RestaurantUser

from .auth import is_developer
from .utils import model_to_dict, slugify_restaurant_name


def get_user_restaurants(user_id):
    db_session = get_session()
    restaurants = db_session.execute(
        select(Restaurant)
        .join(RestaurantUser, RestaurantUser.restaurant_id == Restaurant.id)
        .where(RestaurantUser.user_id == user_id, Restaurant.is_active.is_(True))
        .order_by(Restaurant.name)
    ).scalars().all()
    return [model_to_dict(restaurant) for restaurant in restaurants]


def get_all_restaurants():
    db_session = get_session()
    restaurants = db_session.execute(select(Restaurant).order_by(Restaurant.name)).scalars().all()
    return [model_to_dict(restaurant) for restaurant in restaurants]


def get_current_restaurant():
    restaurant_id = session.get("restaurant_id")
    user_id = session.get("user_id")
    if not restaurant_id or not user_id:
        return None

    db_session = get_session()

    if is_developer():
        restaurant = db_session.execute(
            select(Restaurant).where(Restaurant.id == restaurant_id)
        ).scalar_one_or_none()
    else:
        restaurant = db_session.execute(
            select(Restaurant)
            .join(RestaurantUser, RestaurantUser.restaurant_id == Restaurant.id)
            .where(Restaurant.id == restaurant_id, RestaurantUser.user_id == user_id)
        ).scalar_one_or_none()

    return model_to_dict(restaurant) if restaurant else None


def require_restaurant():
    restaurant = get_current_restaurant()
    if restaurant:
        return restaurant
    flash("Сначала выберите ресторан.", "error")
    return None


def category_belongs_to_restaurant(category_id, restaurant_id):
    db_session = get_session()
    category = db_session.execute(
        select(Category.id).where(Category.id == category_id, Category.restaurant_id == restaurant_id)
    ).first()
    return {"id": category[0]} if category else None


def menu_item_belongs_to_restaurant(item_id, restaurant_id):
    db_session = get_session()
    menu_item = db_session.execute(
        select(MenuItem.id).where(MenuItem.id == item_id, MenuItem.restaurant_id == restaurant_id)
    ).first()
    return {"id": menu_item[0]} if menu_item else None


def menu_item_name_is_available(name, restaurant_id, exclude_id=None):
    db_session = get_session()
    query = select(MenuItem.id).where(MenuItem.restaurant_id == restaurant_id, MenuItem.name == name)
    if exclude_id:
        query = query.where(MenuItem.id != exclude_id)
    return db_session.execute(query).first() is None


def get_accessible_restaurants():
    if not session.get("user_id"):
        return []
    if is_developer():
        return get_all_restaurants()
    return get_user_restaurants(session["user_id"])


def slug_is_available(slug, exclude_id=None):
    db_session = get_session()
    query = select(Restaurant.id).where(Restaurant.slug == slug)
    if exclude_id:
        query = query.where(Restaurant.id != exclude_id)
    return db_session.execute(query).first() is None


def unique_restaurant_slug(name):
    base_slug = slugify_restaurant_name(name)
    slug = base_slug
    suffix = 2

    while not slug_is_available(slug):
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    return slug


def restaurant_form_is_valid(data):
    if not data["name"] or not data["slug"]:
        flash("Укажите название и slug.", "error")
        return False

    return True


def menu_item_form_data():
    return {
        "name": request.form.get("name", "").strip(),
        "price": request.form.get("price"),
        "category_id": request.form.get("category_id"),
    }


def menu_item_form_is_valid(data, restaurant_id):
    if not data["name"] or not data["price"] or not data["category_id"]:
        flash("Укажите название, цену и категорию.", "error")
        return False

    if not menu_item_name_is_available(data["name"], restaurant_id):
        flash("Блюдо с таким названием уже существует.", "error")
        return False

    return True


def max_category_sort_order(db_session, restaurant_id):
    max_sort = db_session.execute(
        select(func.max(Category.sort_order)).where(Category.restaurant_id == restaurant_id)
    ).scalar_one()
    return int(max_sort if max_sort is not None else -1)


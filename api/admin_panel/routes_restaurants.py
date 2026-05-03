from datetime import date

from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import select

from database.db import get_session, session_scope
from database.models import Restaurant, RestaurantUser

from . import admin
from .auth import developer_required, is_developer, login_required
from .queries import (
    get_all_restaurants,
    restaurant_form_is_valid,
    slug_is_available,
    unique_restaurant_slug,
)
from .utils import (
    SLUG_PATTERN,
    allowed_file,
    delete_menu_image,
    model_to_dict,
    restaurant_form_data,
    save_restaurant_logo,
)


@admin.route("/select-restaurant/<int:restaurant_id>")
@login_required
def select_restaurant(restaurant_id):
    db_session = get_session()
    if is_developer():
        restaurant = db_session.execute(
            select(Restaurant.id).where(Restaurant.id == restaurant_id)
        ).first()
    else:
        restaurant = db_session.execute(
            select(Restaurant.id)
            .join(RestaurantUser, RestaurantUser.restaurant_id == Restaurant.id)
            .where(Restaurant.id == restaurant_id, RestaurantUser.user_id == session["user_id"])
        ).first()

    if not restaurant:
        abort(403)

    session["restaurant_id"] = restaurant_id
    next_page = request.args.get("next")
    if next_page == "dashboard":
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("admin.menu"))


@admin.route("/restaurants")
@developer_required
def restaurants():
    restaurants = get_all_restaurants()
    return render_template("admin/restaurants.html", restaurants=restaurants)


@admin.route("/restaurants/check-slug")
@developer_required
def check_restaurant_slug():
    slug = request.args.get("slug", "").strip().lower()
    exclude_id = request.args.get("exclude_id", type=int)

    if not slug:
        return jsonify({"valid": False, "available": False, "message": "Введите slug."})

    if not SLUG_PATTERN.match(slug):
        return jsonify(
            {
                "valid": False,
                "available": False,
                "message": "Только латиница, цифры и дефисы.",
            }
        )

    available = slug_is_available(slug, exclude_id)
    return jsonify(
        {
            "valid": True,
            "available": available,
            "message": "Slug свободен." if available else "Slug уже занят.",
        }
    )


@admin.route("/restaurants/add", methods=["GET", "POST"])
@developer_required
def add_restaurant():
    if request.method == "GET":
        return redirect(url_for("admin.restaurants"))

    if request.method == "POST":
        data = restaurant_form_data()
        data["slug"] = unique_restaurant_slug(data["name"])

        if restaurant_form_is_valid(data):
            try:
                with session_scope() as db_session:
                    db_session.add(
                        Restaurant(
                            name=data["name"],
                            slug=data["slug"],
                            phone=data["phone"],
                            address=data["address"],
                            description=data["description"],
                            classic_info=data["classic_info"],
                            work_hours=data["work_hours"],
                            admin_contact=data["admin_contact"],
                            director_contact=data["director_contact"],
                            email=data["email"],
                            opening_date=date.fromisoformat(data["opening_date"]) if data["opening_date"] else None,
                            support_phone=data["support_phone"],
                            support_email=data["support_email"],
                            map_2gis_url=data["map_2gis_url"],
                            map_2gis_embed_url=data["map_2gis_embed_url"],
                            created_by=session["user_id"],
                        )
                    )
                flash("Ресторан создан.", "success")
                return redirect(url_for("admin.restaurants"))
            except Exception as exc:
                flash(f"Не удалось создать ресторан: {exc}", "error")

    return redirect(url_for("admin.restaurants"))


@admin.route("/restaurants/edit/<int:restaurant_id>", methods=["GET", "POST"])
@developer_required
def edit_restaurant(restaurant_id):
    db_session = get_session()
    restaurant_model = db_session.get(Restaurant, restaurant_id)
    if not restaurant_model:
        abort(404)
    restaurant = model_to_dict(restaurant_model)

    if request.method == "GET":
        return render_template("admin/edit_restaurant.html", restaurant=restaurant)

    if request.method == "POST":
        data = restaurant_form_data()
        data["slug"] = data["slug"].strip()
        is_active = 1 if request.form.get("is_active") == "on" else 0
        logo = request.files.get("logo")
        logo_path = restaurant.get("logo")

        if restaurant_form_is_valid(data):
            if not slug_is_available(data["slug"], restaurant_id):
                flash("Slug уже занят.", "error")
                restaurant.update(data)
                restaurant["is_active"] = is_active
                return render_template("admin/edit_restaurant.html", restaurant=restaurant)

            try:
                if logo and allowed_file(logo.filename):
                    delete_menu_image(logo_path)
                    logo_path = save_restaurant_logo(logo, {"slug": data["slug"]})

                with session_scope() as managed_session:
                    managed_restaurant = managed_session.get(Restaurant, restaurant_id)
                    managed_restaurant.name = data["name"]
                    managed_restaurant.slug = data["slug"]
                    managed_restaurant.phone = data["phone"]
                    managed_restaurant.address = data["address"]
                    managed_restaurant.description = data["description"]
                    managed_restaurant.classic_info = data["classic_info"]
                    managed_restaurant.work_hours = data["work_hours"]
                    managed_restaurant.admin_contact = data["admin_contact"]
                    managed_restaurant.director_contact = data["director_contact"]
                    managed_restaurant.email = data["email"]
                    managed_restaurant.opening_date = date.fromisoformat(data["opening_date"]) if data["opening_date"] else None
                    managed_restaurant.support_phone = data["support_phone"]
                    managed_restaurant.support_email = data["support_email"]
                    managed_restaurant.map_2gis_url = data["map_2gis_url"]
                    managed_restaurant.map_2gis_embed_url = data["map_2gis_embed_url"]
                    managed_restaurant.logo = logo_path
                    managed_restaurant.is_active = bool(is_active)
                flash("Ресторан обновлен.", "success")
                return redirect(url_for("admin.restaurants"))
            except Exception as exc:
                flash(f"Не удалось обновить ресторан: {exc}", "error")

    restaurant.update(data)
    restaurant["is_active"] = is_active
    return render_template("admin/edit_restaurant.html", restaurant=restaurant)


@admin.route("/restaurants/toggle-active/<int:restaurant_id>", methods=["POST"])
@developer_required
def toggle_restaurant_active(restaurant_id):
    db_session = get_session()
    restaurant = db_session.get(Restaurant, restaurant_id)
    if not restaurant:
        abort(404)

    is_active = 1 if request.form.get("is_active") == "on" else 0

    with session_scope() as managed_session:
        managed_restaurant = managed_session.get(Restaurant, restaurant_id)
        managed_restaurant.is_active = bool(is_active)

    flash("Ресторан включен." if is_active else "Ресторан выключен.", "success")
    return redirect(url_for("admin.restaurants"))


@admin.route("/restaurants/delete/<int:restaurant_id>", methods=["POST"])
@developer_required
def delete_restaurant(restaurant_id):
    db_session = get_session()
    restaurant = db_session.get(Restaurant, restaurant_id)
    if not restaurant:
        abort(404)

    with session_scope() as managed_session:
        managed_restaurant = managed_session.get(Restaurant, restaurant_id)
        managed_session.delete(managed_restaurant)
    if session.get("restaurant_id") == restaurant_id:
        session.pop("restaurant_id", None)
    flash("Ресторан удален.", "success")
    return redirect(url_for("admin.restaurants"))

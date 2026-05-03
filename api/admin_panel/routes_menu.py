from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from database.db import get_session, session_scope
from database.models import Category, MenuItem

from . import admin
from .auth import login_required
from .queries import (
    category_belongs_to_restaurant,
    menu_item_belongs_to_restaurant,
    menu_item_name_is_available,
    require_restaurant,
)
from .utils import (
    allowed_file,
    delete_menu_image,
    form_checkbox_value,
    model_to_dict,
    save_menu_image,
)


@admin.route("/categories")
@login_required
def categories():
    return redirect(url_for("admin.menu"))


@admin.route("/categories/add", methods=["POST"])
@login_required
def add_category():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    name = request.form.get("name", "").strip()
    if name:
        try:
            with session_scope() as db_session:
                max_sort = db_session.execute(
                    select(func.max(Category.sort_order)).where(Category.restaurant_id == restaurant["id"])
                ).scalar_one()
                sort_order = int(max_sort if max_sort is not None else -1) + 1
                db_session.add(Category(restaurant_id=restaurant["id"], name=name, sort_order=sort_order))
            flash("Категория добавлена.", "success")
        except Exception as exc:
            message = str(exc)
            if "1062" in message or "Duplicate entry" in message:
                flash("Категория с таким названием уже существует.", "error")
            else:
                flash(f"Не удалось добавить категорию: {exc}", "error")

    return redirect(url_for("admin.menu"))


@admin.route("/categories/reorder", methods=["POST"])
@login_required
def reorder_categories():
    restaurant = require_restaurant()
    if not restaurant:
        return jsonify({"ok": False, "message": "Restaurant is required."}), 400

    payload = request.get_json(silent=True, cache=False) or {}
    category_ids = payload.get("category_ids", [])
    if not isinstance(category_ids, list) or not category_ids:
        return jsonify({"ok": False, "message": "Category ids are required."}), 400

    try:
        category_ids = [int(category_id) for category_id in category_ids]
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "Category ids must be numbers."}), 400

    if len(category_ids) != len(set(category_ids)):
        return jsonify({"ok": False, "message": "Category ids must be unique."}), 400

    try:
        with session_scope() as db_session:
            category_models = db_session.execute(
                select(Category).where(
                    Category.restaurant_id == restaurant["id"],
                    Category.id.in_(category_ids),
                )
            ).scalars().all()
            if {category.id for category in category_models} != set(category_ids):
                return jsonify({"ok": False, "message": "Unknown category."}), 400
            category_map = {category.id: category for category in category_models}
            for sort_order, category_id in enumerate(category_ids):
                category_map[category_id].sort_order = sort_order
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500

    return jsonify({"ok": True})


@admin.route("/categories/edit/<int:id>", methods=["POST"])
@login_required
def edit_category(id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    name = request.form.get("name", "").strip()
    if name:
        try:
            with session_scope() as db_session:
                category = db_session.execute(
                    select(Category).where(Category.id == id, Category.restaurant_id == restaurant["id"])
                ).scalar_one_or_none()
                if not category:
                    abort(404)
                category.name = name
            flash("Категория обновлена.", "success")
        except Exception as exc:
            message = str(exc)
            if "1062" in message or "Duplicate entry" in message:
                flash("Категория с таким названием уже существует.", "error")
            else:
                flash(f"Не удалось обновить категорию: {exc}", "error")

    return redirect(url_for("admin.menu"))


@admin.route("/categories/delete/<int:id>", methods=["POST"])
@login_required
def delete_category(id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    db_session = get_session()
    count = db_session.execute(
        select(func.count()).select_from(MenuItem).where(
            MenuItem.category_id == id,
            MenuItem.restaurant_id == restaurant["id"],
        )
    ).scalar_one()

    if count > 0:
        flash("Нельзя удалить категорию, в которой есть блюда.", "error")
    else:
        with session_scope() as managed_session:
            category = managed_session.execute(
                select(Category).where(Category.id == id, Category.restaurant_id == restaurant["id"])
            ).scalar_one_or_none()
            if category:
                managed_session.delete(category)
        flash("Категория удалена.", "success")

    return redirect(url_for("admin.menu"))


@admin.route("/menu")
@login_required
def menu():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    db_session = get_session()
    menu_models = db_session.execute(
        select(MenuItem)
        .outerjoin(Category, MenuItem.category_id == Category.id)
        .options(joinedload(MenuItem.category))
        .where(MenuItem.restaurant_id == restaurant["id"])
        .order_by(Category.sort_order, Category.name, MenuItem.sort_order, MenuItem.name)
    ).scalars().all()

    menu_items = []
    for item in menu_models:
        item_data = model_to_dict(item)
        item_data["category_name"] = item.category.name if item.category else None
        menu_items.append(item_data)

    categories = [
        model_to_dict(category)
        for category in db_session.execute(
            select(Category)
            .where(Category.restaurant_id == restaurant["id"])
            .order_by(Category.sort_order, Category.name)
        ).scalars().all()
    ]

    return render_template(
        "admin/menu.html",
        menu_items=menu_items,
        categories=categories,
        restaurant=restaurant,
    )


@admin.route("/menu/add", methods=["GET", "POST"])
@login_required
def add_menu_item():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    if request.method == "GET":
        return redirect(url_for("admin.menu"))

    if request.method != "POST":
        return redirect(url_for("admin.menu"))

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip() or None
    ingredients = request.form.get("ingredients", "").strip() or None
    price = request.form.get("price")
    amount = request.form.get("amount", "").strip() or None
    category_id = request.form.get("category_id")
    is_available = form_checkbox_value("is_available")
    image = request.files.get("image")
    image_path = None

    if name and price and category_id:
        if not menu_item_name_is_available(name, restaurant["id"]):
            flash("Блюдо с таким названием уже существует.", "error")
            return redirect(url_for("admin.menu"))

        try:
            category_id_int = int(category_id)
        except (TypeError, ValueError):
            flash("Категория должна быть корректным числом.", "error")
            return redirect(url_for("admin.add_menu_item"))

        if not category_belongs_to_restaurant(category_id_int, restaurant["id"]):
            flash("Категория не принадлежит выбранному ресторану.", "error")
            return redirect(url_for("admin.add_menu_item"))

        if image and image.filename and allowed_file(image.filename):
            image_path = save_menu_image(image, restaurant)

        try:
            with session_scope() as db_session:
                db_session.add(
                    MenuItem(
                        restaurant_id=restaurant["id"],
                        name=name,
                        description=description,
                        ingredients=ingredients,
                        price=int(price),
                        amount=amount,
                        image=image_path,
                        category_id=category_id_int,
                        is_available=bool(is_available),
                    )
                )
            flash("Блюдо добавлено.", "success")
            return redirect(url_for("admin.menu"))
        except Exception as exc:
            message = str(exc)
            if "1062" in message or "Duplicate entry" in message:
                flash("Блюдо с таким названием уже существует.", "error")
            else:
                flash(f"Не удалось добавить блюдо: {exc}", "error")

    return redirect(url_for("admin.menu"))


@admin.route("/menu/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_menu_item(id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    if request.method == "GET":
        return redirect(url_for("admin.menu"))

    if request.method != "POST":
        return redirect(url_for("admin.menu"))

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip() or None
    ingredients = request.form.get("ingredients", "").strip() or None
    price = request.form.get("price")
    amount = request.form.get("amount", "").strip() or None
    category_id = request.form.get("category_id")
    is_available = form_checkbox_value("is_available")
    image = request.files.get("image")
    image_path = request.form.get("current_image")

    if name and price and category_id:
        if not menu_item_name_is_available(name, restaurant["id"], exclude_id=id):
            flash("Блюдо с таким названием уже существует.", "error")
            return redirect(url_for("admin.menu"))

        try:
            category_id_int = int(category_id)
        except (TypeError, ValueError):
            flash("Категория должна быть корректным числом.", "error")
            return redirect(url_for("admin.edit_menu_item", id=id))

        if not category_belongs_to_restaurant(category_id_int, restaurant["id"]):
            flash("Категория не принадлежит выбранному ресторану.", "error")
            return redirect(url_for("admin.edit_menu_item", id=id))

        if image and image.filename and allowed_file(image.filename):
            delete_menu_image(image_path)
            image_path = save_menu_image(image, restaurant)

        try:
            with session_scope() as db_session:
                menu_item = db_session.execute(
                    select(MenuItem).where(MenuItem.id == id, MenuItem.restaurant_id == restaurant["id"])
                ).scalar_one_or_none()
                if not menu_item:
                    abort(404)
                menu_item.name = name
                menu_item.description = description
                menu_item.ingredients = ingredients
                menu_item.price = int(price)
                menu_item.amount = amount
                menu_item.image = image_path
                menu_item.category_id = category_id_int
                menu_item.is_available = bool(is_available)
            flash("Блюдо обновлено.", "success")
            return redirect(url_for("admin.menu"))
        except Exception as exc:
            message = str(exc)
            if "1062" in message or "Duplicate entry" in message:
                flash("Блюдо с таким названием уже существует.", "error")
            else:
                flash(f"Не удалось обновить блюдо: {exc}", "error")

    return redirect(url_for("admin.menu"))


@admin.route("/menu/toggle-available/<int:id>", methods=["POST"])
@login_required
def toggle_menu_item_available(id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    if not menu_item_belongs_to_restaurant(id, restaurant["id"]):
        abort(404)

    is_available = 1 if request.form.get("is_available") == "on" else 0

    with session_scope() as db_session:
        menu_item = db_session.execute(
            select(MenuItem).where(MenuItem.id == id, MenuItem.restaurant_id == restaurant["id"])
        ).scalar_one_or_none()
        if not menu_item:
            abort(404)
        menu_item.is_available = bool(is_available)

    flash("Блюдо включено." if is_available else "Блюдо выключено.", "success")
    return redirect(url_for("admin.menu"))


@admin.route("/menu/delete/<int:id>", methods=["POST"])
@login_required
def delete_menu_item(id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    db_session = get_session()
    item = db_session.execute(
        select(MenuItem).where(MenuItem.id == id, MenuItem.restaurant_id == restaurant["id"])
    ).scalar_one_or_none()
    if not item:
        abort(404)

    image_path = item.image
    with session_scope() as managed_session:
        managed_item = managed_session.get(MenuItem, id)
        managed_session.delete(managed_item)
    if image_path:
        delete_menu_image(image_path)

    flash("Блюдо удалено.", "success")
    return redirect(url_for("admin.menu"))

import json

from flask import flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import func, select

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from database.db import session_scope
from database.models import Category, MenuItem
from services.menu_seed_generator import generate_menu_seed

from . import admin
from .auth import login_required
from .queries import require_restaurant
from .utils import safe_int


@admin.route("/menu-generator")
@login_required
def menu_generator():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/menu_generator.html", restaurant=restaurant)


@admin.route("/api/menu-generator", methods=["POST"])
@login_required
def generate_menu_seed_api():
    restaurant = require_restaurant()
    if not restaurant:
        return jsonify({"ok": False, "message": "Restaurant not selected"}), 400

    payload = request.get_json(silent=True) or {}
    cuisine = (payload.get("cuisine") or "").strip()
    concept = (payload.get("concept") or "").strip()
    language = (payload.get("language") or "ru").strip() or "ru"
    category_count = safe_int(payload.get("category_count"), default=5, minimum=1, maximum=12)
    items_per_category = safe_int(payload.get("items_per_category"), default=6, minimum=1, maximum=20)

    if not cuisine or not concept:
        return jsonify({"ok": False, "message": "Cuisine and concept are required"}), 400

    try:
        generated = generate_menu_seed(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            model=DEEPSEEK_MODEL,
            restaurant_name=restaurant["name"],
            cuisine=cuisine,
            concept=concept,
            language=language,
            category_count=category_count,
            items_per_category=items_per_category,
        )
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500

    return jsonify({"ok": True, "generated_menu": generated})


@admin.route("/menu-generator/import", methods=["POST"])
@login_required
def import_generated_menu():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    raw_payload = request.form.get("generated_menu_json", "").strip()
    if not raw_payload:
        flash("Сначала сгенерируйте меню.", "error")
        return redirect(url_for("admin.menu_generator"))

    try:
        generated_menu = json.loads(raw_payload)
    except json.JSONDecodeError:
        flash("Не удалось прочитать сгенерированное меню.", "error")
        return redirect(url_for("admin.menu_generator"))

    categories = generated_menu.get("categories", [])
    if not categories:
        flash("В сгенерированном меню нет категорий.", "error")
        return redirect(url_for("admin.menu_generator"))

    created_categories = 0
    created_items = 0

    try:
        with session_scope() as db_session:
            max_sort_order = db_session.execute(
                select(func.max(Category.sort_order)).where(Category.restaurant_id == restaurant["id"])
            ).scalar_one()
            category_sort_order = int(max_sort_order if max_sort_order is not None else -1) + 1

            existing_categories = {
                str(row.name).strip().lower(): row.id
                for row in db_session.execute(
                    select(Category.id, Category.name).where(Category.restaurant_id == restaurant["id"])
                ).all()
            }

            existing_items = {
                str(row.name).strip().lower()
                for row in db_session.execute(
                    select(MenuItem.name).where(MenuItem.restaurant_id == restaurant["id"])
                ).all()
            }

            for category in categories:
                category_name = str(category.get("name") or "").strip()
                if not category_name:
                    continue

                category_key = category_name.lower()
                category_id = existing_categories.get(category_key)

                if not category_id:
                    new_category = Category(
                        restaurant_id=restaurant["id"],
                        name=category_name,
                        sort_order=category_sort_order,
                    )
                    db_session.add(new_category)
                    db_session.flush()
                    category_id = new_category.id
                    existing_categories[category_key] = category_id
                    category_sort_order += 1
                    created_categories += 1

                for item in category.get("items", []):
                    item_name = str(item.get("name") or "").strip()
                    if not item_name:
                        continue

                    item_key = item_name.lower()
                    if item_key in existing_items:
                        continue

                    db_session.add(
                        MenuItem(
                            restaurant_id=restaurant["id"],
                            name=item_name,
                            description=str(item.get("description") or "").strip() or None,
                            amount=str(item.get("amount") or "").strip() or None,
                            price=safe_int(item.get("price"), default=0, minimum=0),
                            image=None,
                            category_id=category_id,
                            is_available=True,
                        )
                    )
                    existing_items.add(item_key)
                    created_items += 1
    except Exception as exc:
        flash(f"Не удалось импортировать меню: {exc}", "error")
        return redirect(url_for("admin.menu_generator"))

    flash(
        f"Импорт завершён: категорий добавлено {created_categories}, блюд добавлено {created_items}.",
        "success",
    )
    return redirect(url_for("admin.menu"))

from flask import abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from werkzeug.security import generate_password_hash

from database.db import get_session, session_scope
from database.models import RestaurantUser, User

from . import admin
from .auth import developer_required
from .queries import get_all_restaurants
from .utils import (
    allowed_file,
    delete_resource_file,
    model_to_dict,
    save_user_avatar,
    selected_restaurant_ids,
)


def assign_user_restaurants(db_session, user_id, restaurant_ids):
    for restaurant_id in restaurant_ids:
        db_session.add(
            RestaurantUser(
                restaurant_id=restaurant_id,
                user_id=user_id,
            )
        )


@admin.route("/users")
@developer_required
def users():
    db_session = get_session()
    user_models = db_session.execute(
        select(User)
        .options(selectinload(User.restaurant_links).selectinload(RestaurantUser.restaurant))
        .order_by(User.created_at.desc())
    ).scalars().all()
    users = []
    for user in user_models:
        linked_restaurants = sorted(
            [link.restaurant for link in user.restaurant_links if link.restaurant],
            key=lambda restaurant: restaurant.name,
        )
        user_data = model_to_dict(user)
        user_data["restaurants"] = ", ".join(restaurant.name for restaurant in linked_restaurants) or None
        user_data["restaurant_ids"] = ",".join(str(restaurant.id) for restaurant in linked_restaurants) or None
        users.append(user_data)
    restaurants = get_all_restaurants()
    return render_template("admin/users.html", users=users, restaurants=restaurants)


@admin.route("/users/add", methods=["POST"])
@developer_required
def add_user():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    global_role = request.form.get("global_role", "user")
    restaurant_ids = selected_restaurant_ids()
    avatar = request.files.get("avatar")
    avatar_path = None

    if global_role not in ("developer", "user"):
        abort(400)

    if not name or not email or not password:
        flash("Укажите имя, email и пароль.", "error")
        return redirect(url_for("admin.users"))

    try:
        if avatar and avatar.filename and allowed_file(avatar.filename):
            avatar_path = save_user_avatar(avatar)

        with session_scope() as db_session:
            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                global_role=global_role,
                avatar=avatar_path,
                is_active=True,
            )
            db_session.add(user)
            db_session.flush()
            if restaurant_ids and global_role == "user":
                assign_user_restaurants(db_session, user.id, restaurant_ids)
        flash("Пользователь создан.", "success")
    except Exception as exc:
        if avatar_path:
            delete_resource_file(avatar_path)
        flash(f"Не удалось создать пользователя: {exc}", "error")

    return redirect(url_for("admin.users"))


@admin.route("/users/edit/<int:user_id>", methods=["POST"])
@developer_required
def edit_user(user_id):
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    global_role = request.form.get("global_role", "user")
    is_active = 1 if request.form.get("is_active") == "on" else 0
    restaurant_ids = selected_restaurant_ids()
    avatar = request.files.get("avatar")
    db_session = get_session()
    existing_user = db_session.get(User, user_id)

    if not existing_user:
        abort(404)

    avatar_path = existing_user.avatar
    previous_avatar_path = avatar_path

    if global_role not in ("developer", "user"):
        abort(400)

    if not name or not email:
        flash("Укажите имя и email.", "error")
        return redirect(url_for("admin.users"))

    try:
        if avatar and avatar.filename and allowed_file(avatar.filename):
            avatar_path = save_user_avatar(avatar)

        with session_scope() as managed_session:
            managed_user = managed_session.get(User, user_id)
            managed_user.name = name
            managed_user.email = email
            managed_user.global_role = global_role
            managed_user.avatar = avatar_path
            managed_user.is_active = bool(is_active)
            if password:
                managed_user.password_hash = generate_password_hash(password)
            managed_session.query(RestaurantUser).filter_by(user_id=user_id).delete()
            if restaurant_ids and global_role == "user":
                assign_user_restaurants(managed_session, user_id, restaurant_ids)
        if avatar_path != previous_avatar_path:
            delete_resource_file(previous_avatar_path)
        flash("Пользователь обновлен.", "success")
    except Exception as exc:
        flash(f"Не удалось обновить пользователя: {exc}", "error")

    return redirect(url_for("admin.users"))


@admin.route("/users/delete/<int:user_id>", methods=["POST"])
@developer_required
def delete_user(user_id):
    if user_id == session.get("user_id"):
        flash("Нельзя удалить свой аккаунт.", "error")
        return redirect(url_for("admin.users"))

    db_session = get_session()
    user = db_session.get(User, user_id)
    if not user:
        abort(404)

    avatar_path = user.avatar
    with session_scope() as managed_session:
        managed_user = managed_session.get(User, user_id)
        managed_session.delete(managed_user)
    if avatar_path:
        delete_resource_file(avatar_path)
    flash("Пользователь удален.", "success")
    return redirect(url_for("admin.users"))


@admin.route("/users/toggle-active/<int:user_id>", methods=["POST"])
@developer_required
def toggle_user_active(user_id):
    if user_id == session.get("user_id") and request.form.get("is_active") != "on":
        flash("Нельзя выключить свой аккаунт.", "error")
        return redirect(url_for("admin.users"))

    db_session = get_session()
    user = db_session.get(User, user_id)
    if not user:
        abort(404)

    is_active = 1 if request.form.get("is_active") == "on" else 0

    with session_scope() as managed_session:
        managed_user = managed_session.get(User, user_id)
        managed_user.is_active = bool(is_active)

    flash("Пользователь включен." if is_active else "Пользователь выключен.", "success")
    return redirect(url_for("admin.users"))

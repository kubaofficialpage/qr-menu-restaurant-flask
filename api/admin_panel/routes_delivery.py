from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash

from database.db import get_session, session_scope
from database.models import Operator, RestaurantBranch

from . import admin
from .auth import login_required
from .queries import require_restaurant
from .utils import (
    allowed_file,
    delete_resource_file,
    model_to_dict,
    save_branch_qr_image,
    save_operator_avatar,
)


def serialize_branch(branch):
    return model_to_dict(branch)


def serialize_operator(operator):
    data = model_to_dict(operator)
    data["branch_name"] = operator.branch.name if operator.branch else None
    return data


@admin.route("/branches")
@login_required
def branches():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    db_session = get_session()
    branch_models = db_session.execute(
        select(RestaurantBranch)
        .where(RestaurantBranch.restaurant_id == restaurant["id"])
        .order_by(RestaurantBranch.created_at.desc())
    ).scalars().all()
    return render_template(
        "admin/branches.html",
        restaurant=restaurant,
        branches=[serialize_branch(branch) for branch in branch_models],
    )


@admin.route("/branches/add", methods=["POST"])
@login_required
def add_branch():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    name = request.form.get("name", "").strip()
    address = request.form.get("address", "").strip()
    delivery_fee = request.form.get("delivery_fee", type=int) or 0
    is_active = request.form.get("is_active") == "on"
    qr_code = request.files.get("qr_code")
    qr_path = None

    if not name or not address:
        flash("Укажите название и адрес филиала.", "error")
        return redirect(url_for("admin.branches"))

    try:
        if qr_code and qr_code.filename and allowed_file(qr_code.filename):
            qr_path = save_branch_qr_image(qr_code)

        with session_scope() as db_session:
            db_session.add(
                RestaurantBranch(
                    restaurant_id=restaurant["id"],
                    name=name,
                    address=address,
                    delivery_fee=max(0, delivery_fee),
                    qr_code_image=qr_path,
                    is_active=bool(is_active),
                )
            )
        flash("Филиал создан.", "success")
    except Exception as exc:
        if qr_path:
            delete_resource_file(qr_path)
        flash(f"Не удалось создать филиал: {exc}", "error")

    return redirect(url_for("admin.branches"))


@admin.route("/branches/edit/<int:branch_id>", methods=["POST"])
@login_required
def edit_branch(branch_id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    db_session = get_session()
    branch = db_session.execute(
        select(RestaurantBranch)
        .where(RestaurantBranch.id == branch_id, RestaurantBranch.restaurant_id == restaurant["id"])
    ).scalar_one_or_none()
    if not branch:
        abort(404)

    name = request.form.get("name", "").strip()
    address = request.form.get("address", "").strip()
    delivery_fee = request.form.get("delivery_fee", type=int) or 0
    is_active = request.form.get("is_active") == "on"
    qr_code = request.files.get("qr_code")
    qr_path = branch.qr_code_image
    previous_qr_path = qr_path

    if not name or not address:
        flash("Укажите название и адрес филиала.", "error")
        return redirect(url_for("admin.branches"))

    try:
        if qr_code and qr_code.filename and allowed_file(qr_code.filename):
            qr_path = save_branch_qr_image(qr_code)

        with session_scope() as managed_session:
            managed_branch = managed_session.get(RestaurantBranch, branch_id)
            managed_branch.name = name
            managed_branch.address = address
            managed_branch.delivery_fee = max(0, delivery_fee)
            managed_branch.qr_code_image = qr_path
            managed_branch.is_active = bool(is_active)
        if qr_path != previous_qr_path:
            delete_resource_file(previous_qr_path)
        flash("Филиал обновлен.", "success")
    except Exception as exc:
        flash(f"Не удалось обновить филиал: {exc}", "error")

    return redirect(url_for("admin.branches"))


@admin.route("/branches/toggle-active/<int:branch_id>", methods=["POST"])
@login_required
def toggle_branch_active(branch_id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    db_session = get_session()
    branch = db_session.execute(
        select(RestaurantBranch)
        .where(RestaurantBranch.id == branch_id, RestaurantBranch.restaurant_id == restaurant["id"])
    ).scalar_one_or_none()
    if not branch:
        abort(404)

    is_active = request.form.get("is_active") == "on"
    with session_scope() as managed_session:
        managed_branch = managed_session.get(RestaurantBranch, branch_id)
        managed_branch.is_active = bool(is_active)

    flash("Филиал включен." if is_active else "Филиал выключен.", "success")
    return redirect(url_for("admin.branches"))


@admin.route("/branches/delete/<int:branch_id>", methods=["POST"])
@login_required
def delete_branch(branch_id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    db_session = get_session()
    branch = db_session.execute(
        select(RestaurantBranch)
        .where(RestaurantBranch.id == branch_id, RestaurantBranch.restaurant_id == restaurant["id"])
    ).scalar_one_or_none()
    if not branch:
        abort(404)

    qr_path = branch.qr_code_image
    with session_scope() as managed_session:
        managed_branch = managed_session.get(RestaurantBranch, branch_id)
        managed_session.delete(managed_branch)
    delete_resource_file(qr_path)
    flash("Филиал удален.", "success")
    return redirect(url_for("admin.branches"))


@admin.route("/operators")
@login_required
def operators():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    db_session = get_session()
    operator_models = db_session.execute(
        select(Operator)
        .options(joinedload(Operator.branch))
        .where(Operator.restaurant_id == restaurant["id"])
        .order_by(Operator.created_at.desc())
    ).scalars().all()
    branch_models = db_session.execute(
        select(RestaurantBranch)
        .where(RestaurantBranch.restaurant_id == restaurant["id"])
        .order_by(RestaurantBranch.name)
    ).scalars().all()
    return render_template(
        "admin/operators.html",
        restaurant=restaurant,
        operators=[serialize_operator(operator) for operator in operator_models],
        branches=[serialize_branch(branch) for branch in branch_models],
    )


@admin.route("/operators/add", methods=["POST"])
@login_required
def add_operator():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    full_name = request.form.get("full_name", "").strip()
    login = request.form.get("login", "").strip().lower()
    password = request.form.get("password", "")
    position = request.form.get("position", "").strip() or "Оператор"
    branch_id = request.form.get("branch_id", type=int)
    is_active = request.form.get("is_active") == "on"
    avatar = request.files.get("avatar")
    avatar_path = None

    if not full_name or not login or not password:
        flash("Укажите ФИО, логин и пароль.", "error")
        return redirect(url_for("admin.operators"))

    db_session = get_session()
    if db_session.execute(select(Operator.id).where(Operator.login == login)).first():
        flash("Оператор с таким логином уже существует.", "error")
        return redirect(url_for("admin.operators"))

    if branch_id:
        branch = db_session.execute(
            select(RestaurantBranch.id).where(
                RestaurantBranch.id == branch_id,
                RestaurantBranch.restaurant_id == restaurant["id"],
            )
        ).first()
        if not branch:
            flash("Выбранный филиал не найден.", "error")
            return redirect(url_for("admin.operators"))

    try:
        if avatar and avatar.filename and allowed_file(avatar.filename):
            avatar_path = save_operator_avatar(avatar)

        with session_scope() as managed_session:
            managed_session.add(
                Operator(
                    restaurant_id=restaurant["id"],
                    branch_id=branch_id,
                    full_name=full_name,
                    avatar=avatar_path,
                    login=login,
                    password_hash=generate_password_hash(password),
                    position=position,
                    is_active=bool(is_active),
                )
            )
        flash("Оператор создан.", "success")
    except Exception as exc:
        if avatar_path:
            delete_resource_file(avatar_path)
        flash(f"Не удалось создать оператора: {exc}", "error")

    return redirect(url_for("admin.operators"))


@admin.route("/operators/edit/<int:operator_id>", methods=["POST"])
@login_required
def edit_operator(operator_id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    db_session = get_session()
    operator = db_session.execute(
        select(Operator)
        .where(Operator.id == operator_id, Operator.restaurant_id == restaurant["id"])
    ).scalar_one_or_none()
    if not operator:
        abort(404)

    full_name = request.form.get("full_name", "").strip()
    login = request.form.get("login", "").strip().lower()
    password = request.form.get("password", "")
    position = request.form.get("position", "").strip() or "Оператор"
    branch_id = request.form.get("branch_id", type=int)
    is_active = request.form.get("is_active") == "on"
    avatar = request.files.get("avatar")
    avatar_path = operator.avatar
    previous_avatar_path = avatar_path

    if not full_name or not login:
        flash("Укажите ФИО и логин.", "error")
        return redirect(url_for("admin.operators"))

    existing_login = db_session.execute(
        select(Operator.id).where(Operator.login == login, Operator.id != operator_id)
    ).first()
    if existing_login:
        flash("Оператор с таким логином уже существует.", "error")
        return redirect(url_for("admin.operators"))

    if branch_id:
        branch = db_session.execute(
            select(RestaurantBranch.id).where(
                RestaurantBranch.id == branch_id,
                RestaurantBranch.restaurant_id == restaurant["id"],
            )
        ).first()
        if not branch:
            flash("Выбранный филиал не найден.", "error")
            return redirect(url_for("admin.operators"))

    try:
        if avatar and avatar.filename and allowed_file(avatar.filename):
            avatar_path = save_operator_avatar(avatar)

        with session_scope() as managed_session:
            managed_operator = managed_session.get(Operator, operator_id)
            managed_operator.full_name = full_name
            managed_operator.login = login
            managed_operator.position = position
            managed_operator.branch_id = branch_id
            managed_operator.avatar = avatar_path
            managed_operator.is_active = bool(is_active)
            if password:
                managed_operator.password_hash = generate_password_hash(password)
        if avatar_path != previous_avatar_path:
            delete_resource_file(previous_avatar_path)
        flash("Оператор обновлен.", "success")
    except Exception as exc:
        flash(f"Не удалось обновить оператора: {exc}", "error")

    return redirect(url_for("admin.operators"))


@admin.route("/operators/toggle-active/<int:operator_id>", methods=["POST"])
@login_required
def toggle_operator_active(operator_id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    db_session = get_session()
    operator = db_session.execute(
        select(Operator)
        .where(Operator.id == operator_id, Operator.restaurant_id == restaurant["id"])
    ).scalar_one_or_none()
    if not operator:
        abort(404)

    is_active = request.form.get("is_active") == "on"
    with session_scope() as managed_session:
        managed_operator = managed_session.get(Operator, operator_id)
        managed_operator.is_active = bool(is_active)

    flash("Оператор включен." if is_active else "Оператор выключен.", "success")
    return redirect(url_for("admin.operators"))


@admin.route("/operators/delete/<int:operator_id>", methods=["POST"])
@login_required
def delete_operator(operator_id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    db_session = get_session()
    operator = db_session.execute(
        select(Operator)
        .where(Operator.id == operator_id, Operator.restaurant_id == restaurant["id"])
    ).scalar_one_or_none()
    if not operator:
        abort(404)

    avatar_path = operator.avatar
    with session_scope() as managed_session:
        managed_operator = managed_session.get(Operator, operator_id)
        managed_session.delete(managed_operator)
    delete_resource_file(avatar_path)
    flash("Оператор удален.", "success")
    return redirect(url_for("admin.operators"))

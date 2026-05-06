from functools import wraps

from flask import Blueprint, abort, redirect, render_template, request, session, url_for
from flask_socketio import emit, join_room
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash

from database.db import get_session, session_scope
from database.extensions import socketio
from database.models import Operator, Order, Restaurant, RestaurantBranch

from .delivery import ORDER_STATUS_LABELS, serialize_order

operator_bp = Blueprint("operator", __name__, url_prefix="/operator")


def current_operator():
    operator_id = session.get("operator_id")
    if not operator_id:
        return None
    db_session = get_session()
    operator = db_session.execute(
        select(Operator)
        .options(joinedload(Operator.branch), joinedload(Operator.restaurant))
        .where(Operator.id == operator_id, Operator.is_active.is_(True))
    ).scalar_one_or_none()
    return operator


def operator_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_operator():
            session.pop("operator_id", None)
            return redirect(url_for("operator.login"))
        return view(*args, **kwargs)

    return wrapper


def get_operator_orders(operator, history=False):
    db_session = get_session()
    query = (
        select(Order)
        .options(joinedload(Order.branch), joinedload(Order.customer), joinedload(Order.items))
        .where(Order.restaurant_id == operator.restaurant_id)
        .order_by(Order.created_at.desc())
    )
    if operator.branch_id:
        query = query.where(Order.branch_id == operator.branch_id)
    if history:
        query = query.where(Order.status.in_(("completed", "cancelled")))
    else:
        query = query.where(Order.status.in_(("new", "accepted", "courier")))
    return db_session.execute(query).unique().scalars().all()


@operator_bp.route("", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form.get("login", "").strip().lower()
        password = request.form.get("password", "")
        db_session = get_session()
        operator = db_session.execute(
            select(Operator)
            .options(joinedload(Operator.branch), joinedload(Operator.restaurant))
            .where(Operator.login == login_value, Operator.is_active.is_(True))
        ).scalar_one_or_none()

        if operator and check_password_hash(operator.password_hash, password):
            session["operator_id"] = operator.id
            return redirect(url_for("operator.dashboard"))

        return render_template("operator/login.html", error="Неверный логин или пароль.")

    return render_template("operator/login.html", error=None)


@operator_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("operator_id", None)
    return redirect(url_for("operator.login"))


@operator_bp.route("/dashboard")
@operator_required
def dashboard():
    operator = current_operator()
    tab = request.args.get("tab", "active")
    history = tab == "history"
    orders = get_operator_orders(operator, history=history)
    return render_template(
        "operator/dashboard.html",
        operator=operator,
        orders=orders,
        tab=tab,
        status_labels=ORDER_STATUS_LABELS,
    )


@operator_bp.route("/orders/<int:order_id>")
@operator_required
def order_detail(order_id):
    operator = current_operator()
    db_session = get_session()
    order = db_session.execute(
        select(Order)
        .options(joinedload(Order.branch), joinedload(Order.customer), joinedload(Order.items))
        .where(Order.id == order_id, Order.restaurant_id == operator.restaurant_id)
    ).unique().scalar_one_or_none()
    if not order:
        abort(404)
    if operator.branch_id and order.branch_id != operator.branch_id:
        abort(403)

    return render_template(
        "operator/order_detail.html",
        operator=operator,
        order=order,
        serialized_order=serialize_order(order),
        status_labels=ORDER_STATUS_LABELS,
    )


@operator_bp.route("/orders/<int:order_id>/update", methods=["POST"])
@operator_required
def update_order(order_id):
    operator = current_operator()
    new_status = request.form.get("status", "").strip()
    delivery_url = request.form.get("yandex_delivery_url", "").strip() or None
    try:
        delivery_fee = int(request.form.get("delivery_fee", "0") or 0)
    except ValueError:
        delivery_fee = 0

    with session_scope() as db_session:
        order = db_session.execute(
            select(Order)
            .where(Order.id == order_id, Order.restaurant_id == operator.restaurant_id)
        ).scalar_one_or_none()
        if not order:
            abort(404)
        if operator.branch_id and order.branch_id != operator.branch_id:
            abort(403)

        order.yandex_delivery_url = delivery_url
        order.delivery_fee = max(0, delivery_fee)
        order.total_amount = max(0, order.subtotal_amount + order.delivery_fee)
        if new_status in ORDER_STATUS_LABELS:
            order.status = new_status
        db_session.flush()
        order_id = order.id

    db_session = get_session()
    order = db_session.execute(
        select(Order)
        .options(joinedload(Order.branch), joinedload(Order.customer), joinedload(Order.items))
        .where(Order.id == order_id)
    ).unique().scalar_one()
    from .delivery import emit_order_event

    emit_order_event(order, "operator_orders_changed")
    return redirect(url_for("operator.order_detail", order_id=order_id))


@socketio.on("join_operator_room")
def on_join_operator_room(data):
    operator = current_operator()
    if not operator:
        return
    branch_id = int((data or {}).get("branchId") or 0)
    if operator.branch_id and operator.branch_id != branch_id:
        return
    join_room(f"operator_branch_{branch_id}")
    join_room(f"restaurant_{operator.restaurant_id}")
    emit("operator_room_joined", {"branchId": branch_id})

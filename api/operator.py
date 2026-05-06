from functools import wraps

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from flask_socketio import emit, join_room
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash

from database.db import get_session, session_scope
from database.extensions import socketio
from database.models import BranchStopListItem, Category, MenuItem, Operator, Order, Restaurant, RestaurantBranch

from .delivery import ORDER_STATUS_LABELS, PAYMENT_STATUS_LABELS, serialize_order, update_order_status_timestamps

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


def operator_has_new_orders(operator):
    db_session = get_session()
    query = select(Order.id).where(Order.restaurant_id == operator.restaurant_id, Order.status == "new")
    if operator.branch_id:
        query = query.where(Order.branch_id == operator.branch_id)
    return db_session.execute(query.limit(1)).first() is not None


def format_order_duration(order):
    final_timestamp = order.completed_at or order.cancelled_at
    if not final_timestamp or not order.created_at:
        return None

    total_seconds = max(0, int((final_timestamp - order.created_at).total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def get_stop_list_groups(operator):
    db_session = get_session()
    stop_list_ids = set()
    if operator.branch_id:
        stop_list_ids = set(
            db_session.execute(
                select(BranchStopListItem.menu_item_id).where(BranchStopListItem.branch_id == operator.branch_id)
            ).scalars().all()
        )
    categories = db_session.execute(
        select(Category)
        .where(Category.restaurant_id == operator.restaurant_id, Category.is_active.is_(True))
        .order_by(Category.sort_order, Category.name)
    ).scalars().all()
    menu_items = db_session.execute(
        select(MenuItem)
        .options(joinedload(MenuItem.category))
        .where(MenuItem.restaurant_id == operator.restaurant_id)
        .order_by(MenuItem.category_id, MenuItem.sort_order, MenuItem.name)
    ).scalars().all()

    grouped = []
    items_by_category_id = {}
    uncategorized_items = []

    for item in menu_items:
        item.branch_is_available = item.is_available and item.id not in stop_list_ids
        if item.category_id:
            items_by_category_id.setdefault(item.category_id, []).append(item)
        else:
            uncategorized_items.append(item)

    for category in categories:
        category_items = items_by_category_id.get(category.id, [])
        if not category_items:
            continue
        grouped.append({"id": category.id, "name": category.name, "items": category_items})

    if uncategorized_items:
        grouped.append({"id": "uncategorized", "name": "Без категории", "items": uncategorized_items})

    return grouped


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
        payment_status_labels=PAYMENT_STATUS_LABELS,
        format_order_duration=format_order_duration,
    )


@operator_bp.route("/stop-list")
@operator_required
def stop_list():
    operator = current_operator()
    branch_missing = not bool(operator.branch_id)
    groups = get_stop_list_groups(operator)
    unavailable_count = sum(1 for group in groups for item in group["items"] if not getattr(item, "branch_is_available", item.is_available))
    total_count = sum(len(group["items"]) for group in groups)
    return render_template(
        "operator/stop_list.html",
        operator=operator,
        groups=groups,
        unavailable_count=unavailable_count,
        total_count=total_count,
        has_new_orders=operator_has_new_orders(operator),
        branch_missing=branch_missing,
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
        payment_status_labels=PAYMENT_STATUS_LABELS,
        format_order_duration=format_order_duration,
    )


@operator_bp.route("/orders/<int:order_id>/update", methods=["POST"])
@operator_required
def update_order(order_id):
    operator = current_operator()
    new_status = request.form.get("status", "").strip()
    new_payment_status = request.form.get("payment_status", "").strip()
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
        if new_payment_status in PAYMENT_STATUS_LABELS:
            order.payment_status = new_payment_status
        if new_status in ORDER_STATUS_LABELS:
            if new_status == "courier" and order.payment_type == "online" and order.payment_status != "paid":
                return redirect(url_for("operator.order_detail", order_id=order.id))
            update_order_status_timestamps(order, new_status)
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


@operator_bp.route("/stop-list/items/<int:item_id>/toggle", methods=["POST"])
@operator_required
def toggle_stop_list_item(item_id):
    operator = current_operator()
    if not operator.branch_id:
        abort(400)

    desired_available = request.form.get("is_available") == "on"

    with session_scope() as db_session:
        item = db_session.execute(
            select(MenuItem).where(MenuItem.id == item_id, MenuItem.restaurant_id == operator.restaurant_id)
        ).scalar_one_or_none()
        if not item:
            abort(404)
        stop_entry = db_session.execute(
            select(BranchStopListItem).where(
                BranchStopListItem.branch_id == operator.branch_id,
                BranchStopListItem.menu_item_id == item.id,
            )
        ).scalar_one_or_none()

        if desired_available:
            if stop_entry:
                db_session.delete(stop_entry)
        elif not stop_entry:
            db_session.add(BranchStopListItem(branch_id=operator.branch_id, menu_item_id=item.id))

    if request.accept_mimetypes.best == "application/json" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "itemId": item_id, "isAvailable": bool(item.is_available and desired_available)})
    return redirect(url_for("operator.stop_list"))


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

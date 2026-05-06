import json
import os
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database.db import get_session, session_scope
from database.extensions import socketio
from database.models import Customer, MenuItem, Order, OrderItem, Restaurant, RestaurantBranch

delivery_api = Blueprint("delivery_api", __name__)

OTP_STUB_CODE = "000000"
CUSTOMER_SESSION_ID_KEY = "customer_id"
CUSTOMER_SESSION_PHONE_KEY = "customer_phone"
CUSTOMER_PENDING_PHONE_KEY = "customer_pending_phone"
CHECKOUT_SUBMISSION_MAP_KEY = "checkout_submission_map"
OTP_ACCEPTED_CODES = {OTP_STUB_CODE, "0000"}

RESOURCE_ROOT = os.path.join("static", "resource")
OPERATOR_AVATAR_FOLDER = os.path.join(RESOURCE_ROOT, "operator_avatars")
ORDER_RECEIPT_FOLDER = os.path.join(RESOURCE_ROOT, "order_receipts")
BRANCH_QR_FOLDER = os.path.join(RESOURCE_ROOT, "branch_qr")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

ORDER_STATUS_LABELS = {
    "new": "Новый",
    "accepted": "Принят",
    "courier": "Передан курьеру",
    "completed": "Завершен",
    "cancelled": "Отменен",
}


def normalize_phone(phone):
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if not digits:
        return ""
    if digits.startswith("8") and len(digits) == 11:
        return f"7{digits[1:]}"
    return digits


def save_uploaded_file(file_storage, upload_folder, relative_prefix):
    filename = (file_storage.filename or "").strip()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return None

    os.makedirs(upload_folder, exist_ok=True)
    final_name = f"{uuid.uuid4().hex}.{extension}"
    final_path = os.path.join(upload_folder, final_name)
    file_storage.save(final_path)
    return f"{relative_prefix}/{final_name}".replace("\\", "/")


def serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def model_to_dict(model):
    return {column.name: serialize_value(getattr(model, column.name)) for column in model.__table__.columns}


def serialize_branch(branch):
    data = model_to_dict(branch)
    data["qr_code_url"] = f"/static/resource/{branch.qr_code_image}" if branch.qr_code_image else None
    return data


def serialize_customer(customer):
    return model_to_dict(customer) if customer else None


def serialize_order(order):
    data = model_to_dict(order)
    data["status_label"] = ORDER_STATUS_LABELS.get(order.status, order.status)
    data["branch"] = serialize_branch(order.branch) if order.branch else None
    data["customer"] = serialize_customer(order.customer)
    data["receipt_url"] = f"/static/resource/{order.receipt_image}" if order.receipt_image else None
    data["items"] = []
    for item in order.items:
        item_data = model_to_dict(item)
        menu_item = getattr(item, "menu_item", None)
        item_data["image_url"] = f"/static/resource/{menu_item.image}" if menu_item and getattr(menu_item, "image", None) else "/static/resource/img/default_food_png.png"
        data["items"].append(item_data)
    data["detail_url"] = f"/order/{order.public_id}" if getattr(order, "public_id", None) else None
    data["can_customer_complete"] = order.status in {"accepted", "courier"}
    return data


def get_checkout_payload(restaurant):
    db_session = get_session()
    branches = db_session.execute(
        select(RestaurantBranch)
        .where(RestaurantBranch.restaurant_id == restaurant.id, RestaurantBranch.is_active.is_(True))
        .order_by(RestaurantBranch.name)
    ).scalars().all()
    return {
        "restaurant": model_to_dict(restaurant),
        "branches": [serialize_branch(branch) for branch in branches],
        "customer": serialize_customer(current_customer()),
        "otpStubCode": OTP_STUB_CODE,
    }


def get_restaurant_or_404(restaurant_slug):
    db_session = get_session()
    restaurant = db_session.execute(
        select(Restaurant).where(Restaurant.slug == restaurant_slug, Restaurant.is_active.is_(True))
    ).scalar_one_or_none()
    return restaurant


def current_customer():
    customer_id = session.get(CUSTOMER_SESSION_ID_KEY)
    if not customer_id:
        return None
    db_session = get_session()
    return db_session.execute(select(Customer).where(Customer.id == customer_id)).scalar_one_or_none()


def sign_in_customer(customer):
    session[CUSTOMER_SESSION_ID_KEY] = customer.id
    session[CUSTOMER_SESSION_PHONE_KEY] = customer.phone_whatsapp
    session.modified = True


def sign_out_customer():
    session.pop(CUSTOMER_SESSION_ID_KEY, None)
    session.pop(CUSTOMER_SESSION_PHONE_KEY, None)
    session.pop(CUSTOMER_PENDING_PHONE_KEY, None)
    session.pop(CHECKOUT_SUBMISSION_MAP_KEY, None)
    session.modified = True


def get_checkout_submission_order(request_id):
    if not request_id:
        return None
    submission_map = session.get(CHECKOUT_SUBMISSION_MAP_KEY) or {}
    order_id = submission_map.get(request_id)
    if not order_id:
        return None

    db_session = get_session()
    return db_session.execute(
        select(Order)
        .options(joinedload(Order.restaurant), joinedload(Order.branch), joinedload(Order.customer), joinedload(Order.items))
        .where(Order.id == order_id)
    ).unique().scalar_one_or_none()


def remember_checkout_submission(request_id, order_id):
    if not request_id:
        return
    submission_map = session.get(CHECKOUT_SUBMISSION_MAP_KEY) or {}
    submission_map[request_id] = order_id
    if len(submission_map) > 20:
        oldest_key = next(iter(submission_map))
        submission_map.pop(oldest_key, None)
    session[CHECKOUT_SUBMISSION_MAP_KEY] = submission_map
    session.modified = True


def ensure_customer_verified(phone, full_name=None, address=None, otp_code=None):
    normalized_phone = normalize_phone(phone)
    if not normalized_phone:
        return None, "Укажите корректный номер WhatsApp."

    existing_customer = current_customer()
    if existing_customer and existing_customer.phone_whatsapp == normalized_phone:
        return existing_customer, None

    if otp_code not in OTP_ACCEPTED_CODES:
        return None, "Подтвердите номер кодом OTP. Временно используется код 0000."

    with session_scope() as db_session:
        customer = db_session.execute(
            select(Customer).where(Customer.phone_whatsapp == normalized_phone)
        ).scalar_one_or_none()
        if customer:
            if full_name:
                customer.full_name = full_name
            if address:
                customer.address = address
        else:
            customer = Customer(
                full_name=full_name or "Гость",
                phone_whatsapp=normalized_phone,
                address=address or None,
            )
            db_session.add(customer)
            db_session.flush()

        db_session.flush()
        sign_in_customer(customer)
        customer_id = customer.id

    customer = get_session().execute(select(Customer).where(Customer.id == customer_id)).scalar_one()
    return customer, None


def next_order_number():
    return f"{datetime.now().strftime('ORD-%d%m-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"


def parse_cart_items(raw_cart):
    try:
        items = json.loads(raw_cart or "[]")
    except json.JSONDecodeError:
        return None
    if not isinstance(items, list):
        return None
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            item_id = int(item.get("id"))
            quantity = int(item.get("qty"))
        except (TypeError, ValueError):
            continue
        if quantity <= 0:
            continue
        normalized.append({"id": item_id, "qty": quantity})
    return normalized


def emit_order_event(order, event_name):
    payload = {
        "orderId": order.id,
        "orderNumber": order.order_number,
        "status": order.status,
        "branchId": order.branch_id,
        "restaurantId": order.restaurant_id,
    }
    if order.branch_id:
        socketio.emit(event_name, payload, room=f"operator_branch_{order.branch_id}")
    socketio.emit(event_name, payload, room=f"restaurant_{order.restaurant_id}")


@delivery_api.route("/api/customer/request-otp", methods=["POST"])
def request_customer_otp():
    payload = request.get_json(silent=True) or {}
    phone = normalize_phone(payload.get("phone"))
    if not phone:
        return jsonify({"ok": False, "message": "Укажите номер WhatsApp."}), 400

    session[CUSTOMER_PENDING_PHONE_KEY] = phone

    db_session = get_session()
    existing = db_session.execute(select(Customer.id).where(Customer.phone_whatsapp == phone)).first() is not None
    return jsonify(
        {
            "ok": True,
            "code": OTP_STUB_CODE,
            "existingCustomer": existing,
            "message": "Код отправлен. Временно используйте 0000.",
        }
    )


@delivery_api.route("/api/customer/verify-otp", methods=["POST"])
def verify_customer_otp():
    payload = request.get_json(silent=True) or {}
    phone = normalize_phone(payload.get("phone"))
    code = str(payload.get("code", "")).strip()
    full_name = (payload.get("fullName") or "").strip()
    address = (payload.get("address") or "").strip()

    if phone != session.get(CUSTOMER_PENDING_PHONE_KEY):
        return jsonify({"ok": False, "message": "Сначала запросите OTP для этого номера."}), 400

    customer, error = ensure_customer_verified(phone, full_name=full_name, address=address, otp_code=code)
    if error:
        return jsonify({"ok": False, "message": error}), 400

    return jsonify({"ok": True, "customer": serialize_customer(customer)})


@delivery_api.route("/api/<restaurant_slug>/checkout/options")
def checkout_options(restaurant_slug):
    restaurant = get_restaurant_or_404(restaurant_slug)
    if not restaurant:
        return jsonify({"ok": False, "message": "Ресторан не найден."}), 404
    return jsonify({"ok": True, **get_checkout_payload(restaurant)})


@delivery_api.route("/api/<restaurant_slug>/orders", methods=["POST"])
def create_order(restaurant_slug):
    restaurant = get_restaurant_or_404(restaurant_slug)
    if not restaurant:
        return jsonify({"ok": False, "message": "Ресторан не найден."}), 404

    existing_customer = current_customer()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()
    comment = request.form.get("comment", "").strip() or None
    otp_code = request.form.get("otp_code", "").strip()
    payment_type = request.form.get("payment_type", "online").strip()
    branch_id = request.form.get("branch_id", "").strip()
    client_request_id = request.form.get("client_request_id", "").strip()
    cart_items = parse_cart_items(request.form.get("cart"))
    receipt_image = request.files.get("receipt")

    if existing_customer:
        full_name = full_name or (existing_customer.full_name or "")
        phone = phone or (existing_customer.phone_whatsapp or "")
        address = address or (existing_customer.address or "")

    repeated_order = get_checkout_submission_order(client_request_id)
    if repeated_order and repeated_order.restaurant_id == restaurant.id:
        if not existing_customer or repeated_order.customer_id == existing_customer.id:
            return jsonify({"ok": True, "order": serialize_order(repeated_order), "duplicate": True})

    if not full_name:
        return jsonify({"ok": False, "message": "Укажите имя клиента."}), 400
    if not phone:
        return jsonify({"ok": False, "message": "Укажите номер WhatsApp."}), 400
    if not address:
        return jsonify({"ok": False, "message": "Укажите адрес доставки."}), 400
    if payment_type not in {"cash", "online"}:
        return jsonify({"ok": False, "message": "Некорректный тип оплаты."}), 400
    if not cart_items:
        return jsonify({"ok": False, "message": "Корзина пуста."}), 400

    customer, error = ensure_customer_verified(phone, full_name=full_name, address=address, otp_code=otp_code)
    if error:
        return jsonify({"ok": False, "message": error}), 400

    db_session = get_session()
    try:
        branch_id = int(branch_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "Выберите филиал."}), 400

    branch = db_session.execute(
        select(RestaurantBranch)
        .where(
            RestaurantBranch.id == branch_id,
            RestaurantBranch.restaurant_id == restaurant.id,
            RestaurantBranch.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if not branch:
        return jsonify({"ok": False, "message": "Филиал не найден."}), 404

    item_ids = [item["id"] for item in cart_items]
    menu_items = db_session.execute(
        select(MenuItem)
        .where(MenuItem.restaurant_id == restaurant.id, MenuItem.id.in_(item_ids), MenuItem.is_available.is_(True))
    ).scalars().all()
    menu_by_id = {item.id: item for item in menu_items}
    if len(menu_by_id) != len(set(item_ids)):
        return jsonify({"ok": False, "message": "Некоторые блюда недоступны."}), 400

    subtotal = 0
    receipt_path = None
    if receipt_image and receipt_image.filename:
        receipt_path = save_uploaded_file(receipt_image, ORDER_RECEIPT_FOLDER, "order_receipts")
        if not receipt_path:
            return jsonify({"ok": False, "message": "Чек должен быть в формате PNG, JPG или WEBP."}), 400

    delivery_fee = max(0, int(getattr(branch, "delivery_fee", 0) or 0))

    with session_scope() as db_session:
        order = Order(
            public_id=uuid.uuid4().hex,
            order_number=next_order_number(),
            restaurant_id=restaurant.id,
            branch_id=branch.id,
            customer_id=customer.id,
            payment_type=payment_type,
            payment_status="receipt_uploaded" if receipt_path else "pending",
            delivery_address=address,
            customer_comment=comment,
            delivery_fee=delivery_fee,
            receipt_image=receipt_path,
        )
        db_session.add(order)
        db_session.flush()

        for cart_item in cart_items:
            menu_item = menu_by_id[cart_item["id"]]
            line_total = menu_item.price * cart_item["qty"]
            subtotal += line_total
            db_session.add(
                OrderItem(
                    order_id=order.id,
                    menu_item_id=menu_item.id,
                    item_name=menu_item.name,
                    item_price=menu_item.price,
                    quantity=cart_item["qty"],
                    amount_label=menu_item.amount,
                )
            )

        order.subtotal_amount = subtotal
        order.total_amount = subtotal + delivery_fee
        db_session.flush()
        created_order_id = order.id

    remember_checkout_submission(client_request_id, created_order_id)

    order = db_session.execute(
        select(Order)
        .options(
            joinedload(Order.restaurant),
            joinedload(Order.branch),
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.menu_item),
        )
        .where(Order.id == created_order_id)
    ).unique().scalar_one()
    emit_order_event(order, "operator_orders_changed")
    return jsonify({"ok": True, "order": serialize_order(order)})


@delivery_api.route("/api/<restaurant_slug>/orders/my")
def my_orders(restaurant_slug):
    restaurant = get_restaurant_or_404(restaurant_slug)
    customer = current_customer()
    if not restaurant or not customer:
        return jsonify({"ok": True, "orders": []})

    db_session = get_session()
    orders = db_session.execute(
        select(Order)
        .options(
            joinedload(Order.restaurant),
            joinedload(Order.branch),
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.menu_item),
        )
        .where(Order.restaurant_id == restaurant.id, Order.customer_id == customer.id)
        .order_by(Order.created_at.desc())
    ).unique().scalars().all()
    return jsonify({"ok": True, "orders": [serialize_order(order) for order in orders]})


@delivery_api.route("/<restaurant_slug>/orders")
def customer_orders_page(restaurant_slug):
    restaurant = get_restaurant_or_404(restaurant_slug)
    if not restaurant:
        return render_template("client/404.html"), 404
    return render_template("client/orders.html", restaurant=model_to_dict(restaurant))


@delivery_api.route("/<restaurant_slug>/checkout")
def customer_checkout_page(restaurant_slug):
    restaurant = get_restaurant_or_404(restaurant_slug)
    if not restaurant:
        return render_template("client/404.html"), 404
    return render_template(
        "client/checkout.html",
        restaurant=model_to_dict(restaurant),
        checkout_data=get_checkout_payload(restaurant),
    )


@delivery_api.route("/<restaurant_slug>/me")
def customer_profile_page(restaurant_slug):
    restaurant = get_restaurant_or_404(restaurant_slug)
    if not restaurant:
        return render_template("client/404.html"), 404
    return render_template(
        "client/profile.html",
        restaurant=model_to_dict(restaurant),
        customer=serialize_customer(current_customer()),
    )


@delivery_api.route("/<restaurant_slug>/me/logout", methods=["POST"])
def customer_logout(restaurant_slug):
    restaurant = get_restaurant_or_404(restaurant_slug)
    if not restaurant:
        return render_template("client/404.html"), 404
    sign_out_customer()
    return redirect(url_for("delivery_api.customer_profile_page", restaurant_slug=restaurant_slug))


@delivery_api.route("/<restaurant_slug>/orders/<int:order_id>")
def customer_order_detail_page(restaurant_slug, order_id):
    restaurant = get_restaurant_or_404(restaurant_slug)
    customer = current_customer()
    if not restaurant or not customer:
        return render_template("client/404.html"), 404

    db_session = get_session()
    order = db_session.execute(
        select(Order)
        .options(
            joinedload(Order.restaurant),
            joinedload(Order.branch),
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.menu_item),
        )
        .where(
            Order.id == order_id,
            Order.restaurant_id == restaurant.id,
            Order.customer_id == customer.id,
        )
    ).unique().scalar_one_or_none()
    if not order:
        return render_template("client/404.html"), 404

    return render_template(
        "client/order_detail.html",
        restaurant=model_to_dict(restaurant),
        order=serialize_order(order),
    )


@delivery_api.route("/order/<public_id>")
def public_order_detail_page(public_id):
    db_session = get_session()
    order = db_session.execute(
        select(Order)
        .options(
            joinedload(Order.restaurant),
            joinedload(Order.branch),
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.menu_item),
        )
        .where(Order.public_id == public_id)
    ).unique().scalar_one_or_none()
    if not order or not order.restaurant:
        return render_template("client/404.html"), 404

    order_data = serialize_order(order)
    customer = current_customer()
    if not customer or order.customer_id != customer.id:
        order_data["can_customer_complete"] = False

    return render_template(
        "client/order_detail.html",
        restaurant=model_to_dict(order.restaurant),
        order=order_data,
    )


@delivery_api.route("/<restaurant_slug>/orders/<int:order_id>/complete", methods=["POST"])
def customer_complete_order(restaurant_slug, order_id):
    restaurant = get_restaurant_or_404(restaurant_slug)
    customer = current_customer()
    if not restaurant or not customer:
        return render_template("client/404.html"), 404

    with session_scope() as db_session:
        order = db_session.execute(
            select(Order).where(
                Order.id == order_id,
                Order.restaurant_id == restaurant.id,
                Order.customer_id == customer.id,
            )
        ).scalar_one_or_none()
        if not order:
            return render_template("client/404.html"), 404
        if order.status not in {"accepted", "courier"}:
            return redirect(
                url_for("delivery_api.customer_order_detail_page", restaurant_slug=restaurant_slug, order_id=order_id)
            )
        order.status = "completed"
        db_session.flush()

    db_session = get_session()
    order = db_session.execute(
        select(Order)
        .options(
            joinedload(Order.restaurant),
            joinedload(Order.branch),
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.menu_item),
        )
        .where(Order.id == order_id)
    ).unique().scalar_one()
    emit_order_event(order, "operator_orders_changed")
    return redirect(url_for("delivery_api.customer_order_detail_page", restaurant_slug=restaurant_slug, order_id=order_id))

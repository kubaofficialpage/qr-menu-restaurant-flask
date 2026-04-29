import os
import re
import uuid
from datetime import date, timedelta
from functools import wraps

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from PIL import Image
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db

admin = Blueprint("admin", __name__, url_prefix="/admin")

UPLOAD_FOLDER = "static/resource/img"
USER_PROFILE_UPLOAD_FOLDER = "static/resource/user_profiles"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def compress_to_webp(input_path, output_path, quality=75, max_size=(800, 800)):
    img = Image.open(input_path)
    img = img.convert("RGBA" if img.mode in ("RGBA", "P") else "RGB")
    img.thumbnail(max_size)
    img.save(output_path, format="WEBP", quality=quality, method=6)


def get_restaurant_upload_folder(restaurant):
    folder = os.path.join(UPLOAD_FOLDER, restaurant["slug"])
    os.makedirs(folder, exist_ok=True)
    return folder


def get_user_profile_upload_folder():
    os.makedirs(USER_PROFILE_UPLOAD_FOLDER, exist_ok=True)
    return USER_PROFILE_UPLOAD_FOLDER


def save_uploaded_image(image, upload_folder, relative_prefix, quality=75, max_size=(800, 800)):
    filename = f"{uuid.uuid4().hex}.webp"
    temp_path = os.path.join(upload_folder, "temp_" + filename)
    final_path = os.path.join(upload_folder, filename)

    image.save(temp_path)
    compress_to_webp(temp_path, final_path, quality=quality, max_size=max_size)
    os.remove(temp_path)

    return f"{relative_prefix}/{filename}"


def save_menu_image(image, restaurant):
    upload_folder = get_restaurant_upload_folder(restaurant)
    return save_uploaded_image(image, upload_folder, f"img/{restaurant['slug']}")


def save_restaurant_logo(image, restaurant):
    return save_menu_image(image, restaurant)


def save_user_avatar(image):
    upload_folder = get_user_profile_upload_folder()
    return save_uploaded_image(image, upload_folder, "user_profiles", quality=80, max_size=(600, 600))


def delete_resource_file(resource_path):
    if not resource_path:
        return

    relative_path = resource_path.replace("\\", "/")
    if not (relative_path.startswith("img/") or relative_path.startswith("user_profiles/")):
        return

    file_path = os.path.normpath(os.path.join("static/resource", relative_path))
    resource_root = os.path.abspath("static/resource")
    absolute_path = os.path.abspath(file_path)

    if not absolute_path.startswith(resource_root):
        return

    if os.path.exists(absolute_path):
        os.remove(absolute_path)


def delete_menu_image(image_path):
    delete_resource_file(image_path)


def fetch_one(query, params=()):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return fetch_one(
        "SELECT id, name, email, global_role, avatar FROM users WHERE id = %s AND is_active = TRUE",
        (user_id,),
    )


def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = uuid.uuid4().hex
        session["csrf_token"] = token
    return token


def rotate_csrf_token():
    session["csrf_token"] = uuid.uuid4().hex
    return session["csrf_token"]


def validate_csrf():
    sent = request.form.get("csrf_token", "")
    token = session.get("csrf_token", "")
    if not sent or not token or sent != token:
        abort(400)


def is_developer():
    return session.get("global_role") == "developer"


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("admin.login"))
        if not current_user():
            session.clear()
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)

    return wrapper


def developer_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("admin.login"))
        if not current_user():
            session.clear()
            return redirect(url_for("admin.login"))
        if not is_developer():
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def get_user_restaurants(user_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT r.*
        FROM restaurants r
        JOIN restaurant_users ru ON ru.restaurant_id = r.id
        WHERE ru.user_id = %s AND r.is_active = TRUE
        ORDER BY r.name
        """,
        (user_id,),
    )
    restaurants = cursor.fetchall()
    cursor.close()
    conn.close()
    return restaurants


def get_all_restaurants():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM restaurants ORDER BY name")
    restaurants = cursor.fetchall()
    cursor.close()
    conn.close()
    return restaurants


def get_current_restaurant():
    restaurant_id = session.get("restaurant_id")
    user_id = session.get("user_id")
    if not restaurant_id or not user_id:
        return None

    if is_developer():
        return fetch_one("SELECT * FROM restaurants WHERE id = %s", (restaurant_id,))

    return fetch_one(
        """
        SELECT r.*
        FROM restaurants r
        JOIN restaurant_users ru ON ru.restaurant_id = r.id
        WHERE r.id = %s AND ru.user_id = %s
        """,
        (restaurant_id, user_id),
    )


def require_restaurant():
    restaurant = get_current_restaurant()
    if restaurant:
        return restaurant
    flash("Сначала выберите ресторан.", "error")
    return None


def category_belongs_to_restaurant(category_id, restaurant_id):
    return fetch_one(
        "SELECT id FROM categories WHERE id = %s AND restaurant_id = %s",
        (category_id, restaurant_id),
    )


def menu_item_belongs_to_restaurant(item_id, restaurant_id):
    return fetch_one(
        "SELECT id FROM menu WHERE id = %s AND restaurant_id = %s",
        (item_id, restaurant_id),
    )


def menu_item_name_is_available(name, restaurant_id, exclude_id=None):
    if exclude_id:
        return not fetch_one(
            """
            SELECT id
            FROM menu
            WHERE restaurant_id = %s AND name = %s AND id <> %s
            """,
            (restaurant_id, name, exclude_id),
        )

    return not fetch_one(
        "SELECT id FROM menu WHERE restaurant_id = %s AND name = %s",
        (restaurant_id, name),
    )


def get_accessible_restaurants():
    if not session.get("user_id"):
        return []
    if is_developer():
        return get_all_restaurants()
    return get_user_restaurants(session["user_id"])


def build_in_clause_params(values):
    if not values:
        return "", ()
    return ", ".join(["%s"] * len(values)), tuple(values)


def fetch_dashboard_analytics(restaurants, current_restaurant):
    restaurant_ids = [restaurant["id"] for restaurant in restaurants]
    if not restaurant_ids:
        return {
            "overview": {
                "restaurants": 0,
                "menu_items": 0,
                "cart_adds": 0,
                "visits": 0,
                "sessions": 0,
            },
            "selected_restaurant": None,
            "daily_labels": [],
            "daily_visits": [],
            "daily_cart_adds": [],
            "top_dishes": [],
            "restaurant_stats": [],
        }

    selected_restaurant = current_restaurant if current_restaurant and current_restaurant["id"] in restaurant_ids else restaurants[0]
    in_clause, params = build_in_clause_params(restaurant_ids)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        f"""
        SELECT
            (SELECT COUNT(*) FROM menu WHERE restaurant_id IN ({in_clause})) AS menu_items,
            (SELECT COUNT(*) FROM menu_cart_events WHERE restaurant_id IN ({in_clause})) AS cart_adds,
            (SELECT COUNT(*) FROM restaurant_visit_events WHERE restaurant_id IN ({in_clause})) AS visits,
            (SELECT COUNT(DISTINCT session_id) FROM restaurant_visit_events WHERE restaurant_id IN ({in_clause})) AS sessions
        """,
        params + params + params + params,
    )
    totals = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            COALESCE((SELECT COUNT(*) FROM menu WHERE restaurant_id = %s), 0) AS menu_items,
            COALESCE((SELECT COUNT(*) FROM categories WHERE restaurant_id = %s), 0) AS categories,
            COALESCE((SELECT COUNT(*) FROM menu_cart_events WHERE restaurant_id = %s), 0) AS cart_adds,
            COALESCE((SELECT COUNT(*) FROM restaurant_visit_events WHERE restaurant_id = %s), 0) AS visits,
            COALESCE((SELECT COUNT(DISTINCT session_id) FROM restaurant_visit_events WHERE restaurant_id = %s), 0) AS sessions
        """,
        (selected_restaurant["id"], selected_restaurant["id"], selected_restaurant["id"], selected_restaurant["id"], selected_restaurant["id"]),
    )
    selected_totals = cursor.fetchone()

    start_date = date.today() - timedelta(days=13)

    cursor.execute(
        """
        SELECT DATE(created_at) AS day, COUNT(*) AS total
        FROM restaurant_visit_events
        WHERE restaurant_id = %s AND created_at >= %s
        GROUP BY DATE(created_at)
        ORDER BY day
        """,
        (selected_restaurant["id"], start_date),
    )
    visit_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT DATE(created_at) AS day, SUM(quantity_delta) AS total
        FROM menu_cart_events
        WHERE restaurant_id = %s AND created_at >= %s
        GROUP BY DATE(created_at)
        ORDER BY day
        """,
        (selected_restaurant["id"], start_date),
    )
    cart_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT m.name, SUM(e.quantity_delta) AS total
        FROM menu_cart_events e
        JOIN menu m ON m.id = e.menu_item_id
        WHERE e.restaurant_id = %s
        GROUP BY e.menu_item_id, m.name
        ORDER BY total DESC, m.name
        LIMIT 7
        """,
        (selected_restaurant["id"],),
    )
    top_dishes = cursor.fetchall()

    cursor.execute(
        f"""
        SELECT
            r.id,
            r.name,
            r.slug,
            COALESCE(v.visits, 0) AS visits,
            COALESCE(v.sessions, 0) AS sessions,
            COALESCE(c.cart_adds, 0) AS cart_adds
        FROM restaurants r
        LEFT JOIN (
            SELECT restaurant_id, COUNT(*) AS visits, COUNT(DISTINCT session_id) AS sessions
            FROM restaurant_visit_events
            WHERE restaurant_id IN ({in_clause})
            GROUP BY restaurant_id
        ) v ON v.restaurant_id = r.id
        LEFT JOIN (
            SELECT restaurant_id, SUM(quantity_delta) AS cart_adds
            FROM menu_cart_events
            WHERE restaurant_id IN ({in_clause})
            GROUP BY restaurant_id
        ) c ON c.restaurant_id = r.id
        WHERE r.id IN ({in_clause})
        ORDER BY visits DESC, r.name
        """,
        params + params + params,
    )
    restaurant_stats = cursor.fetchall()

    cursor.close()
    conn.close()

    visit_map = {row["day"].isoformat(): int(row["total"]) for row in visit_rows}
    cart_map = {row["day"].isoformat(): int(row["total"] or 0) for row in cart_rows}

    daily_labels = []
    daily_visits = []
    daily_cart_adds = []
    for offset in range(14):
        current_day = start_date + timedelta(days=offset)
        key = current_day.isoformat()
        daily_labels.append(current_day.strftime("%d.%m"))
        daily_visits.append(visit_map.get(key, 0))
        daily_cart_adds.append(cart_map.get(key, 0))

    return {
        "overview": {
            "restaurants": len(restaurants),
            "menu_items": int(totals["menu_items"] or 0),
            "cart_adds": int(totals["cart_adds"] or 0),
            "visits": int(totals["visits"] or 0),
            "sessions": int(totals["sessions"] or 0),
        },
        "selected_restaurant": {
            "id": selected_restaurant["id"],
            "name": selected_restaurant["name"],
            "slug": selected_restaurant["slug"],
            "logo": selected_restaurant.get("logo"),
            "menu_items": int(selected_totals["menu_items"] or 0),
            "categories": int(selected_totals["categories"] or 0),
            "cart_adds": int(selected_totals["cart_adds"] or 0),
            "visits": int(selected_totals["visits"] or 0),
            "sessions": int(selected_totals["sessions"] or 0),
        },
        "daily_labels": daily_labels,
        "daily_visits": daily_visits,
        "daily_cart_adds": daily_cart_adds,
        "top_dishes": [
            {"name": row["name"], "total": int(row["total"] or 0)}
            for row in top_dishes
        ],
        "restaurant_stats": [
            {
                "id": row["id"],
                "name": row["name"],
                "slug": row["slug"],
                "visits": int(row["visits"] or 0),
                "sessions": int(row["sessions"] or 0),
                "cart_adds": int(row["cart_adds"] or 0),
            }
            for row in restaurant_stats
        ],
    }


def selected_restaurant_ids():
    restaurant_ids = []
    for restaurant_id in request.form.getlist("restaurant_ids"):
        if restaurant_id.isdigit():
            restaurant_ids.append(int(restaurant_id))
    return restaurant_ids


def form_checkbox_value(name):
    return 1 if request.form.get(name) == "on" else 0


def assign_user_restaurants(cursor, user_id, restaurant_ids):
    for restaurant_id in restaurant_ids:
        cursor.execute(
            """
            INSERT IGNORE INTO restaurant_users (restaurant_id, user_id, role)
            VALUES (%s, %s, 'restaurant_admin')
            """,
            (restaurant_id, user_id),
        )


def restaurant_form_data():
    return {
        "name": request.form.get("name", "").strip(),
        "slug": request.form.get("slug", "").strip().lower(),
        "phone": request.form.get("phone", "").strip() or None,
        "address": request.form.get("address", "").strip() or None,
        "description": request.form.get("description", "").strip() or None,
        "classic_info": request.form.get("classic_info", "").strip() or None,
        "work_hours": request.form.get("work_hours", "").strip() or None,
        "admin_contact": request.form.get("admin_contact", "").strip() or None,
        "director_contact": request.form.get("director_contact", "").strip() or None,
        "email": request.form.get("email", "").strip().lower() or None,
        "opening_date": request.form.get("opening_date") or None,
        "support_phone": request.form.get("support_phone", "").strip() or None,
        "support_email": request.form.get("support_email", "").strip().lower() or None,
        "map_2gis_url": request.form.get("map_2gis_url", "").strip() or None,
        "map_2gis_embed_url": None,
    }


def slugify_restaurant_name(name):
    translit = str.maketrans({
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
        "ә": "a", "ғ": "g", "қ": "q", "ң": "n", "ө": "o", "ұ": "u",
        "ү": "u", "һ": "h", "і": "i",
    })
    normalized = name.strip().lower().translate(translit)
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return slug or "restaurant"


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
    if not SLUG_PATTERN.match(data["slug"]):
        flash("Slug может содержать только латинские строчные буквы, цифры и дефисы.", "error")
        return False
    return True


def menu_item_form_data():
    return {
        "name": request.form.get("name", "").strip(),
        "price": request.form.get("price"),
        "amount": request.form.get("amount", "").strip() or None,
        "category_id": request.form.get("category_id"),
        "is_available": form_checkbox_value("is_available"),
    }


def menu_item_form_is_valid(data, restaurant_id):
    if not data["name"] or not data["price"] or not data["category_id"]:
        flash("Укажите название, цену и категорию.", "error")
        return False

    try:
        data["price"] = int(data["price"])
        data["category_id"] = int(data["category_id"])
    except (TypeError, ValueError):
        flash("Цена и категория должны быть корректными числами.", "error")
        return False

    if data["price"] < 0:
        flash("Цена не может быть отрицательной.", "error")
        return False

    if not category_belongs_to_restaurant(data["category_id"], restaurant_id):
        flash("Категория не принадлежит выбранному ресторану.", "error")
        return False

    return True


def slug_is_available(slug, exclude_id=None):
    if exclude_id:
        return not fetch_one(
            "SELECT id FROM restaurants WHERE slug = %s AND id <> %s",
            (slug, exclude_id),
        )
    return not fetch_one("SELECT id FROM restaurants WHERE slug = %s", (slug,))


@admin.context_processor
def inject_admin_context():
    return {
        "current_user": current_user(),
        "current_restaurant": get_current_restaurant(),
        "admin_restaurants": get_accessible_restaurants(),
        "is_developer": is_developer(),
        "csrf_token": get_csrf_token(),
    }


@admin.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        validate_csrf()
        email = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        user = fetch_one(
            """
            SELECT id, name, email, password_hash, global_role
            FROM users
            WHERE email = %s AND is_active = TRUE
            """,
            (email,),
        )

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["global_role"] = user["global_role"]
            session.permanent = True
            rotate_csrf_token()
            return redirect(url_for("admin.dashboard"))

        flash("Неверный email или пароль.", "error")

    return render_template("admin/login.html")


@admin.route("/logout", methods=["POST"])
def logout():
    validate_csrf()
    session.clear()
    return redirect(url_for("admin.login"))


@admin.route("/")
@login_required
def dashboard():
    restaurants = get_accessible_restaurants()
    analytics = fetch_dashboard_analytics(restaurants, get_current_restaurant())

    return render_template(
        "admin/dashboard.html",
        restaurants=restaurants,
        analytics=analytics,
    )


@admin.route("/select-restaurant/<int:restaurant_id>")
@login_required
def select_restaurant(restaurant_id):
    if is_developer():
        restaurant = fetch_one("SELECT id FROM restaurants WHERE id = %s", (restaurant_id,))
    else:
        restaurant = fetch_one(
            """
            SELECT r.id
            FROM restaurants r
            JOIN restaurant_users ru ON ru.restaurant_id = r.id
            WHERE r.id = %s AND ru.user_id = %s
            """,
            (restaurant_id, session["user_id"]),
        )

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
        return jsonify({
            "valid": False,
            "available": False,
            "message": "Только латиница, цифры и дефисы.",
        })

    available = slug_is_available(slug, exclude_id)
    return jsonify({
        "valid": True,
        "available": available,
        "message": "Slug свободен." if available else "Slug уже занят.",
    })


@admin.route("/users")
@developer_required
def users():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT u.id, u.name, u.email, u.global_role, u.avatar, u.is_active, u.created_at,
               GROUP_CONCAT(r.name ORDER BY r.name SEPARATOR ', ') AS restaurants,
               GROUP_CONCAT(r.id ORDER BY r.name SEPARATOR ',') AS restaurant_ids
        FROM users u
        LEFT JOIN restaurant_users ru ON ru.user_id = u.id
        LEFT JOIN restaurants r ON r.id = ru.restaurant_id
        GROUP BY u.id, u.name, u.email, u.global_role, u.avatar, u.is_active, u.created_at
        ORDER BY u.created_at DESC
        """
    )
    users = cursor.fetchall()
    cursor.execute("SELECT * FROM restaurants ORDER BY name")
    restaurants = cursor.fetchall()
    cursor.close()
    conn.close()
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

    conn = get_db()
    cursor = conn.cursor()
    try:
        if avatar and avatar.filename and allowed_file(avatar.filename):
            avatar_path = save_user_avatar(avatar)

        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, global_role, avatar, is_active)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            """,
            (name, email, generate_password_hash(password), global_role, avatar_path),
        )
        user_id = cursor.lastrowid
        if restaurant_ids and global_role == "user":
            assign_user_restaurants(cursor, user_id, restaurant_ids)
        conn.commit()
        flash("Пользователь создан.", "success")
    except Exception as exc:
        conn.rollback()
        if avatar_path:
            delete_resource_file(avatar_path)
        flash(f"Не удалось создать пользователя: {exc}", "error")
    finally:
        cursor.close()
        conn.close()

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
    existing_user = fetch_one("SELECT avatar FROM users WHERE id = %s", (user_id,))

    if not existing_user:
        abort(404)

    avatar_path = existing_user.get("avatar")
    previous_avatar_path = avatar_path

    if global_role not in ("developer", "user"):
        abort(400)

    if not name or not email:
        flash("Укажите имя и email.", "error")
        return redirect(url_for("admin.users"))

    conn = get_db()
    cursor = conn.cursor()
    try:
        if avatar and avatar.filename and allowed_file(avatar.filename):
            avatar_path = save_user_avatar(avatar)

        if password:
            cursor.execute(
                """
                UPDATE users
                SET name = %s, email = %s, password_hash = %s, global_role = %s, avatar = %s, is_active = %s
                WHERE id = %s
                """,
                (name, email, generate_password_hash(password), global_role, avatar_path, is_active, user_id),
            )
        else:
            cursor.execute(
                """
                UPDATE users
                SET name = %s, email = %s, global_role = %s, avatar = %s, is_active = %s
                WHERE id = %s
                """,
                (name, email, global_role, avatar_path, is_active, user_id),
            )

        cursor.execute("DELETE FROM restaurant_users WHERE user_id = %s", (user_id,))
        if restaurant_ids and global_role == "user":
            assign_user_restaurants(cursor, user_id, restaurant_ids)
        conn.commit()
        if avatar_path != previous_avatar_path:
            delete_resource_file(previous_avatar_path)
        flash("Пользователь обновлен.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Не удалось обновить пользователя: {exc}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("admin.users"))


@admin.route("/users/delete/<int:user_id>", methods=["POST"])
@developer_required
def delete_user(user_id):
    if user_id == session.get("user_id"):
        flash("Нельзя удалить свой аккаунт.", "error")
        return redirect(url_for("admin.users"))

    conn = get_db()
    cursor = conn.cursor()
    user = fetch_one("SELECT avatar FROM users WHERE id = %s", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    if user:
        delete_resource_file(user.get("avatar"))
    flash("Пользователь удален.", "success")
    return redirect(url_for("admin.users"))


@admin.route("/users/toggle-active/<int:user_id>", methods=["POST"])
@developer_required
def toggle_user_active(user_id):
    validate_csrf()

    if user_id == session.get("user_id") and request.form.get("is_active") != "on":
        flash("РќРµР»СЊР·СЏ РІС‹РєР»СЋС‡РёС‚СЊ СЃРІРѕР№ Р°РєРєР°СѓРЅС‚.", "error")
        return redirect(url_for("admin.users"))

    user = fetch_one("SELECT id FROM users WHERE id = %s", (user_id,))
    if not user:
        abort(404)

    is_active = 1 if request.form.get("is_active") == "on" else 0

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET is_active = %s WHERE id = %s",
        (is_active, user_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash("РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ РІРєР»СЋС‡РµРЅ." if is_active else "РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ РІС‹РєР»СЋС‡РµРЅ.", "success")
    return redirect(url_for("admin.users"))


@admin.route("/restaurants/add", methods=["GET", "POST"])
@developer_required
def add_restaurant():
    if request.method == "GET":
        return redirect(url_for("admin.restaurants"))

    if request.method == "POST":
        data = restaurant_form_data()
        data["slug"] = unique_restaurant_slug(data["name"])

        if restaurant_form_is_valid(data):
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO restaurants (
                        name, slug, phone, address, description, classic_info,
                        work_hours, admin_contact, director_contact, email,
                        opening_date, support_phone, support_email, map_2gis_url,
                        map_2gis_embed_url, created_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        data["name"], data["slug"], data["phone"], data["address"],
                        data["description"], data["classic_info"], data["work_hours"],
                        data["admin_contact"], data["director_contact"], data["email"],
                        data["opening_date"], data["support_phone"], data["support_email"],
                        data["map_2gis_url"], data["map_2gis_embed_url"], session["user_id"],
                    ),
                )
                conn.commit()
                flash("Ресторан создан.", "success")
                return redirect(url_for("admin.restaurants"))
            except Exception as exc:
                conn.rollback()
                flash(f"Не удалось создать ресторан: {exc}", "error")
            finally:
                cursor.close()
                conn.close()

    return redirect(url_for("admin.restaurants"))


@admin.route("/restaurants/edit/<int:restaurant_id>", methods=["GET", "POST"])
@developer_required
def edit_restaurant(restaurant_id):
    restaurant = fetch_one("SELECT * FROM restaurants WHERE id = %s", (restaurant_id,))
    if not restaurant:
        abort(404)

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

            conn = get_db()
            cursor = conn.cursor()
            try:
                if logo and allowed_file(logo.filename):
                    delete_menu_image(logo_path)
                    logo_path = save_restaurant_logo(logo, {"slug": data["slug"]})

                cursor.execute(
                    """
                    UPDATE restaurants
                    SET name = %s, slug = %s, phone = %s, address = %s,
                        description = %s, classic_info = %s, work_hours = %s,
                        admin_contact = %s, director_contact = %s, email = %s,
                        opening_date = %s, support_phone = %s, support_email = %s,
                        map_2gis_url = %s, map_2gis_embed_url = %s, logo = %s,
                        is_active = %s
                    WHERE id = %s
                    """,
                    (
                        data["name"], data["slug"], data["phone"], data["address"],
                        data["description"], data["classic_info"], data["work_hours"],
                        data["admin_contact"], data["director_contact"], data["email"],
                        data["opening_date"], data["support_phone"], data["support_email"],
                        data["map_2gis_url"], data["map_2gis_embed_url"], logo_path,
                        is_active, restaurant_id,
                    ),
                )
                conn.commit()
                flash("Ресторан обновлен.", "success")
                return redirect(url_for("admin.restaurants"))
            except Exception as exc:
                conn.rollback()
                flash(f"Не удалось обновить ресторан: {exc}", "error")
            finally:
                cursor.close()
                conn.close()

    restaurant.update(data)
    restaurant["is_active"] = is_active
    return render_template("admin/edit_restaurant.html", restaurant=restaurant)


@admin.route("/restaurants/toggle-active/<int:restaurant_id>", methods=["POST"])
@developer_required
def toggle_restaurant_active(restaurant_id):
    restaurant = fetch_one("SELECT id FROM restaurants WHERE id = %s", (restaurant_id,))
    if not restaurant:
        abort(404)

    is_active = 1 if request.form.get("is_active") == "on" else 0

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE restaurants SET is_active = %s WHERE id = %s",
        (is_active, restaurant_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash("Ресторан включен." if is_active else "Ресторан выключен.", "success")
    return redirect(url_for("admin.restaurants"))


@admin.route("/restaurants/delete/<int:restaurant_id>", methods=["POST"])
@developer_required
def delete_restaurant(restaurant_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM restaurants WHERE id = %s", (restaurant_id,))
    conn.commit()
    cursor.close()
    conn.close()
    if session.get("restaurant_id") == restaurant_id:
        session.pop("restaurant_id", None)
    flash("Ресторан удален.", "success")
    return redirect(url_for("admin.restaurants"))


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
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM categories WHERE restaurant_id = %s",
                (restaurant["id"],),
            )
            sort_order = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO categories (restaurant_id, name, sort_order) VALUES (%s, %s, %s)",
                (restaurant["id"], name, sort_order),
            )
            conn.commit()
            flash("Категория добавлена.", "success")
        except Exception as exc:
            conn.rollback()
            message = str(exc)
            if "1062" in message or "Duplicate entry" in message:
                flash("Категория с таким названием уже существует.", "error")
            else:
                flash(f"Не удалось добавить категорию: {exc}", "error")
        finally:
            cursor.close()
            conn.close()

    return redirect(url_for("admin.menu"))


@admin.route("/categories/reorder", methods=["POST"])
@login_required
def reorder_categories():
    restaurant = require_restaurant()
    if not restaurant:
        return jsonify({"ok": False, "message": "Restaurant is required."}), 400

    category_ids = request.get_json(silent=True, cache=False) or {}
    category_ids = category_ids.get("category_ids", [])
    if not isinstance(category_ids, list) or not category_ids:
        return jsonify({"ok": False, "message": "Category ids are required."}), 400

    try:
        category_ids = [int(category_id) for category_id in category_ids]
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "Category ids must be numbers."}), 400

    if len(category_ids) != len(set(category_ids)):
        return jsonify({"ok": False, "message": "Category ids must be unique."}), 400

    placeholders = ", ".join(["%s"] * len(category_ids))
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            SELECT id
            FROM categories
            WHERE restaurant_id = %s AND id IN ({placeholders})
            """,
            (restaurant["id"], *category_ids),
        )
        existing_ids = {row[0] for row in cursor.fetchall()}
        if existing_ids != set(category_ids):
            return jsonify({"ok": False, "message": "Unknown category."}), 400

        for sort_order, category_id in enumerate(category_ids):
            cursor.execute(
                "UPDATE categories SET sort_order = %s WHERE id = %s AND restaurant_id = %s",
                (sort_order, category_id, restaurant["id"]),
            )

        conn.commit()
    except Exception as exc:
        conn.rollback()
        return jsonify({"ok": False, "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({"ok": True})


@admin.route("/categories/edit/<int:id>", methods=["POST"])
@login_required
def edit_category(id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    name = request.form.get("name", "").strip()
    if name:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE categories SET name = %s WHERE id = %s AND restaurant_id = %s",
                (name, id, restaurant["id"]),
            )
            conn.commit()
            flash("Категория обновлена.", "success")
        except Exception as exc:
            conn.rollback()
            message = str(exc)
            if "1062" in message or "Duplicate entry" in message:
                flash("Категория с таким названием уже существует.", "error")
            else:
                flash(f"Не удалось обновить категорию: {exc}", "error")
        finally:
            cursor.close()
            conn.close()

    return redirect(url_for("admin.menu"))


@admin.route("/categories/delete/<int:id>", methods=["POST"])
@login_required
def delete_category(id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM menu WHERE category_id = %s AND restaurant_id = %s",
        (id, restaurant["id"]),
    )
    count = cursor.fetchone()[0]

    if count > 0:
        flash("Нельзя удалить категорию, в которой есть блюда.", "error")
    else:
        cursor.execute(
            "DELETE FROM categories WHERE id = %s AND restaurant_id = %s",
            (id, restaurant["id"]),
        )
        conn.commit()
        flash("Категория удалена.", "success")

    cursor.close()
    conn.close()
    return redirect(url_for("admin.menu"))


@admin.route("/menu")
@login_required
def menu():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT m.*, c.name AS category_name
        FROM menu m
        LEFT JOIN categories c ON m.category_id = c.id
        WHERE m.restaurant_id = %s
        ORDER BY c.sort_order, c.name, m.sort_order, m.name
        """,
        (restaurant["id"],),
    )
    menu_items = cursor.fetchall()
    cursor.execute(
        "SELECT * FROM categories WHERE restaurant_id = %s ORDER BY sort_order, name",
        (restaurant["id"],),
    )
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
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

    if request.method == "POST":
        name = request.form.get("name", "").strip()
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
                category_id = int(category_id)
            except (TypeError, ValueError):
                flash("Категория должна быть корректным числом.", "error")
                return redirect(url_for("admin.add_menu_item"))

            if not category_belongs_to_restaurant(category_id, restaurant["id"]):
                flash("Категория не принадлежит выбранному ресторану.", "error")
                return redirect(url_for("admin.add_menu_item"))

            if image and allowed_file(image.filename):
                image_path = save_menu_image(image, restaurant)

            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO menu (restaurant_id, name, price, amount, image, category_id, is_available)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (restaurant["id"], name, int(price), amount, image_path, category_id, is_available),
                )
                conn.commit()
                flash("Блюдо добавлено.", "success")
                return redirect(url_for("admin.menu"))
            except Exception as exc:
                conn.rollback()
                message = str(exc)
                if "1062" in message or "Duplicate entry" in message:
                    flash("Блюдо с таким названием уже существует.", "error")
                else:
                    flash(f"Не удалось добавить блюдо: {exc}", "error")
            finally:
                cursor.close()
                conn.close()

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM categories WHERE restaurant_id = %s ORDER BY sort_order, name",
        (restaurant["id"],),
    )
    categories = cursor.fetchall()
    cursor.close()
    conn.close()

    return redirect(url_for("admin.menu"))


@admin.route("/menu/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_menu_item(id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    if request.method == "GET":
        return redirect(url_for("admin.menu"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price")
        amount = request.form.get("amount", "").strip() or None
        category_id = request.form.get("category_id")
        is_available = form_checkbox_value("is_available")
        image = request.files.get("image")
        image_path = request.form.get("current_image")

        if name and price and category_id:
            if not menu_item_name_is_available(name, restaurant["id"], exclude_id=id):
                flash("Блюдо с таким названием уже существует.", "error")
                cursor.close()
                conn.close()
                return redirect(url_for("admin.menu"))

            try:
                category_id = int(category_id)
            except (TypeError, ValueError):
                flash("Категория должна быть корректным числом.", "error")
                cursor.close()
                conn.close()
                return redirect(url_for("admin.edit_menu_item", id=id))

            if not category_belongs_to_restaurant(category_id, restaurant["id"]):
                flash("Категория не принадлежит выбранному ресторану.", "error")
                cursor.close()
                conn.close()
                return redirect(url_for("admin.edit_menu_item", id=id))

            if image and allowed_file(image.filename):
                delete_menu_image(image_path)
                image_path = save_menu_image(image, restaurant)

            try:
                cursor.execute(
                    """
                    UPDATE menu
                    SET name = %s, price = %s, amount = %s, image = %s,
                        category_id = %s, is_available = %s
                    WHERE id = %s AND restaurant_id = %s
                    """,
                    (
                        name, int(price), amount, image_path, category_id,
                        is_available, id, restaurant["id"],
                    ),
                )
                conn.commit()
                flash("Блюдо обновлено.", "success")
                cursor.close()
                conn.close()
                return redirect(url_for("admin.menu"))
            except Exception as exc:
                conn.rollback()
                message = str(exc)
                if "1062" in message or "Duplicate entry" in message:
                    flash("Блюдо с таким названием уже существует.", "error")
                else:
                    flash(f"Не удалось обновить блюдо: {exc}", "error")

    cursor.execute(
        "SELECT * FROM menu WHERE id = %s AND restaurant_id = %s",
        (id, restaurant["id"]),
    )
    menu_item = cursor.fetchone()
    cursor.execute(
        "SELECT * FROM categories WHERE restaurant_id = %s ORDER BY sort_order, name",
        (restaurant["id"],),
    )
    categories = cursor.fetchall()
    cursor.close()
    conn.close()

    if not menu_item:
        abort(404)

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

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE menu SET is_available = %s WHERE id = %s AND restaurant_id = %s",
        (is_available, id, restaurant["id"]),
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash("Блюдо включено." if is_available else "Блюдо выключено.", "success")
    return redirect(url_for("admin.menu"))


@admin.route("/menu/delete/<int:id>", methods=["POST"])
@login_required
def delete_menu_item(id):
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT image FROM menu WHERE id = %s AND restaurant_id = %s",
        (id, restaurant["id"]),
    )
    item = cursor.fetchone()

    if item and item["image"]:
        delete_menu_image(item["image"])

    cursor.execute(
        "DELETE FROM menu WHERE id = %s AND restaurant_id = %s",
        (id, restaurant["id"]),
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash("Блюдо удалено.", "success")
    return redirect(url_for("admin.menu"))

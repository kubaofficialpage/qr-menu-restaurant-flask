from api.admin_panel import admin

"""

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    language = (payload.get("language") or "ru").strip() or "ru"

    if not name:
        return jsonify({"ok": False, "message": "Dish name is required"}), 400

    try:
        text = generate_dish_description(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            model=DEEPSEEK_MODEL,
            dish_name=name,
            language=language,
        )
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500

    return jsonify({"ok": True, "description": text})


def get_accessible_restaurants():
    if not session.get("user_id"):
        return []
    if is_developer():
        return get_all_restaurants()
    return get_user_restaurants(session["user_id"])


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
    db_session = get_session()
    start_date = date.today() - timedelta(days=13)
    selected_restaurant_id = selected_restaurant["id"]

    totals = {
        "menu_items": db_session.execute(
            select(func.count()).select_from(MenuItem).where(MenuItem.restaurant_id.in_(restaurant_ids))
        ).scalar_one(),
        "cart_adds": db_session.execute(
            select(func.count()).select_from(MenuCartEvent).where(MenuCartEvent.restaurant_id.in_(restaurant_ids))
        ).scalar_one(),
        "visits": db_session.execute(
            select(func.count()).select_from(RestaurantVisitEvent).where(RestaurantVisitEvent.restaurant_id.in_(restaurant_ids))
        ).scalar_one(),
        "sessions": db_session.execute(
            select(func.count(distinct(RestaurantVisitEvent.session_id)))
            .where(RestaurantVisitEvent.restaurant_id.in_(restaurant_ids))
        ).scalar_one(),
    }

    selected_totals = {
        "menu_items": db_session.execute(
            select(func.count()).select_from(MenuItem).where(MenuItem.restaurant_id == selected_restaurant_id)
        ).scalar_one(),
        "categories": db_session.execute(
            select(func.count()).select_from(Category).where(Category.restaurant_id == selected_restaurant_id)
        ).scalar_one(),
        "cart_adds": db_session.execute(
            select(func.count()).select_from(MenuCartEvent).where(MenuCartEvent.restaurant_id == selected_restaurant_id)
        ).scalar_one(),
        "visits": db_session.execute(
            select(func.count()).select_from(RestaurantVisitEvent).where(RestaurantVisitEvent.restaurant_id == selected_restaurant_id)
        ).scalar_one(),
        "sessions": db_session.execute(
            select(func.count(distinct(RestaurantVisitEvent.session_id)))
            .where(RestaurantVisitEvent.restaurant_id == selected_restaurant_id)
        ).scalar_one(),
    }

    visit_rows = db_session.execute(
        select(
            func.date(RestaurantVisitEvent.created_at).label("day"),
            func.count().label("total"),
        )
        .where(
            RestaurantVisitEvent.restaurant_id == selected_restaurant_id,
            RestaurantVisitEvent.created_at >= start_date,
        )
        .group_by(func.date(RestaurantVisitEvent.created_at))
        .order_by("day")
    ).all()

    cart_rows = db_session.execute(
        select(
            func.date(MenuCartEvent.created_at).label("day"),
            func.sum(MenuCartEvent.quantity_delta).label("total"),
        )
        .where(
            MenuCartEvent.restaurant_id == selected_restaurant_id,
            MenuCartEvent.created_at >= start_date,
        )
        .group_by(func.date(MenuCartEvent.created_at))
        .order_by("day")
    ).all()

    top_dishes = db_session.execute(
        select(
            MenuItem.name.label("name"),
            func.sum(MenuCartEvent.quantity_delta).label("total"),
        )
        .join(MenuItem, MenuItem.id == MenuCartEvent.menu_item_id)
        .where(MenuCartEvent.restaurant_id == selected_restaurant_id)
        .group_by(MenuCartEvent.menu_item_id, MenuItem.name)
        .order_by(func.sum(MenuCartEvent.quantity_delta).desc(), MenuItem.name)
        .limit(7)
    ).all()

    visit_stats_rows = db_session.execute(
        select(
            RestaurantVisitEvent.restaurant_id.label("restaurant_id"),
            func.count().label("visits"),
            func.count(distinct(RestaurantVisitEvent.session_id)).label("sessions"),
        )
        .where(RestaurantVisitEvent.restaurant_id.in_(restaurant_ids))
        .group_by(RestaurantVisitEvent.restaurant_id)
    ).all()
    cart_stats_rows = db_session.execute(
        select(
            MenuCartEvent.restaurant_id.label("restaurant_id"),
            func.sum(MenuCartEvent.quantity_delta).label("cart_adds"),
        )
        .where(MenuCartEvent.restaurant_id.in_(restaurant_ids))
        .group_by(MenuCartEvent.restaurant_id)
    ).all()

    visit_stats_map = {
        row.restaurant_id: {"visits": int(row.visits or 0), "sessions": int(row.sessions or 0)}
        for row in visit_stats_rows
    }
    cart_stats_map = {
        row.restaurant_id: int(row.cart_adds or 0)
        for row in cart_stats_rows
    }
    restaurant_stats = sorted(
        [
            {
                "id": restaurant["id"],
                "name": restaurant["name"],
                "slug": restaurant["slug"],
                "visits": visit_stats_map.get(restaurant["id"], {}).get("visits", 0),
                "sessions": visit_stats_map.get(restaurant["id"], {}).get("sessions", 0),
                "cart_adds": cart_stats_map.get(restaurant["id"], 0),
            }
            for restaurant in restaurants
        ],
        key=lambda item: (-item["visits"], item["name"]),
    )

    visit_map = {day_key(row.day): int(row.total) for row in visit_rows}
    cart_map = {day_key(row.day): int(row.total or 0) for row in cart_rows}

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
            {"name": row.name, "total": int(row.total or 0)}
            for row in top_dishes
        ],
        "restaurant_stats": restaurant_stats,
    }


def selected_restaurant_ids():
    restaurant_ids = []
    for restaurant_id in request.form.getlist("restaurant_ids"):
        if restaurant_id.isdigit():
            restaurant_ids.append(int(restaurant_id))
    return restaurant_ids


def form_checkbox_value(name):
    return 1 if request.form.get(name) == "on" else 0


def safe_int(value, default=0, minimum=None, maximum=None):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default

    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def assign_user_restaurants(db_session, user_id, restaurant_ids):
    for restaurant_id in restaurant_ids:
        db_session.add(
            RestaurantUser(
                restaurant_id=restaurant_id,
                user_id=user_id,
                role="restaurant_admin",
            )
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
    db_session = get_session()
    query = select(Restaurant.id).where(Restaurant.slug == slug)
    if exclude_id:
        query = query.where(Restaurant.id != exclude_id)
    return db_session.execute(query).first() is None


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

        db_session = get_session()
        user = db_session.execute(
            select(User).where(User.email == email, User.is_active.is_(True))
        ).scalar_one_or_none()

        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            session["global_role"] = user.global_role
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


@admin.route("/qr")
@login_required
def qr_generator():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    restaurant_url = url_for("restaurant_home", restaurant_slug=restaurant["slug"], _external=True)
    return render_template(
        "admin/qr_generator.html",
        restaurant=restaurant,
        restaurant_url=restaurant_url,
        qr_template_path=str(TEMPLATE_QR_PATH).replace("\\", "/"),
    )


@admin.route("/qr/preview")
@login_required
def qr_preview():
    restaurant = require_restaurant()
    if not restaurant:
        abort(404)

    restaurant_url = url_for("restaurant_home", restaurant_slug=restaurant["slug"], _external=True)
    preview_buffer = build_restaurant_qr_preview(
        restaurant_url=restaurant_url,
        restaurant_name=restaurant["name"],
        logo_resource_path=restaurant.get("logo"),
    )
    return send_file(preview_buffer, mimetype="image/png")


@admin.route("/qr/download")
@login_required
def qr_download():
    restaurant = require_restaurant()
    if not restaurant:
        return redirect(url_for("admin.dashboard"))

    restaurant_url = url_for("restaurant_home", restaurant_slug=restaurant["slug"], _external=True)
    pdf_buffer = build_restaurant_qr_pdf(
        template_path=TEMPLATE_QR_PATH,
        restaurant_url=restaurant_url,
        restaurant_name=restaurant["name"],
        logo_resource_path=restaurant.get("logo"),
    )
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{restaurant['slug']}-qr-a4.pdf",
    )


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
    validate_csrf()
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
    validate_csrf()

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

    try:
        with session_scope() as db_session:
            category_models = db_session.execute(
                select(Category)
                .where(Category.restaurant_id == restaurant["id"], Category.id.in_(category_ids))
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

    if request.method == "POST":
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
                category_id = int(category_id)
            except (TypeError, ValueError):
                flash("Категория должна быть корректным числом.", "error")
                return redirect(url_for("admin.add_menu_item"))

            if not category_belongs_to_restaurant(category_id, restaurant["id"]):
                flash("Категория не принадлежит выбранному ресторану.", "error")
                return redirect(url_for("admin.add_menu_item"))

            if image and allowed_file(image.filename):
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
                            category_id=category_id,
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

    if request.method == "POST":
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
                category_id = int(category_id)
            except (TypeError, ValueError):
                flash("Категория должна быть корректным числом.", "error")
                return redirect(url_for("admin.edit_menu_item", id=id))

            if not category_belongs_to_restaurant(category_id, restaurant["id"]):
                flash("Категория не принадлежит выбранному ресторану.", "error")
                return redirect(url_for("admin.edit_menu_item", id=id))

            if image and allowed_file(image.filename):
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
                    menu_item.category_id = category_id
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

"""

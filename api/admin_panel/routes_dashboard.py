from datetime import date, timedelta

from flask import render_template
from sqlalchemy import distinct, func, select

from database.db import get_session
from database.models import Category, MenuCartEvent, MenuItem, RestaurantVisitEvent

from . import admin
from .auth import login_required
from .queries import get_accessible_restaurants, get_current_restaurant
from .utils import day_key


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

    selected_restaurant = (
        current_restaurant
        if current_restaurant and current_restaurant["id"] in restaurant_ids
        else restaurants[0]
    )
    db_session = get_session()
    start_date = date.today() - timedelta(days=13)
    selected_restaurant_id = selected_restaurant["id"]

    totals = {
        "menu_items": db_session.execute(
            select(func.count())
            .select_from(MenuItem)
            .where(MenuItem.restaurant_id.in_(restaurant_ids))
        ).scalar_one(),
        "cart_adds": db_session.execute(
            select(func.count())
            .select_from(MenuCartEvent)
            .where(MenuCartEvent.restaurant_id.in_(restaurant_ids))
        ).scalar_one(),
        "visits": db_session.execute(
            select(func.count())
            .select_from(RestaurantVisitEvent)
            .where(RestaurantVisitEvent.restaurant_id.in_(restaurant_ids))
        ).scalar_one(),
        "sessions": db_session.execute(
            select(func.count(distinct(RestaurantVisitEvent.session_id))).where(
                RestaurantVisitEvent.restaurant_id.in_(restaurant_ids)
            )
        ).scalar_one(),
    }

    selected_totals = {
        "menu_items": db_session.execute(
            select(func.count())
            .select_from(MenuItem)
            .where(MenuItem.restaurant_id == selected_restaurant_id)
        ).scalar_one(),
        "categories": db_session.execute(
            select(func.count())
            .select_from(Category)
            .where(Category.restaurant_id == selected_restaurant_id)
        ).scalar_one(),
        "cart_adds": db_session.execute(
            select(func.count())
            .select_from(MenuCartEvent)
            .where(MenuCartEvent.restaurant_id == selected_restaurant_id)
        ).scalar_one(),
        "visits": db_session.execute(
            select(func.count())
            .select_from(RestaurantVisitEvent)
            .where(RestaurantVisitEvent.restaurant_id == selected_restaurant_id)
        ).scalar_one(),
        "sessions": db_session.execute(
            select(func.count(distinct(RestaurantVisitEvent.session_id))).where(
                RestaurantVisitEvent.restaurant_id == selected_restaurant_id
            )
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
        row.restaurant_id: {
            "visits": int(row.visits or 0),
            "sessions": int(row.sessions or 0),
        }
        for row in visit_stats_rows
    }
    cart_stats_map = {row.restaurant_id: int(row.cart_adds or 0) for row in cart_stats_rows}

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
        "top_dishes": [{"name": row.name, "total": int(row.total or 0)} for row in top_dishes],
        "restaurant_stats": restaurant_stats,
    }


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

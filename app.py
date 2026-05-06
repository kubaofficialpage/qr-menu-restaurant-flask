import os
from datetime import timedelta

from flask import Flask, abort, redirect, render_template, request, session, url_for
from dotenv import load_dotenv
from api.menu import get_active_restaurants, get_restaurant_by_slug, get_restaurant_by_slug_any_status, menu_api
from api.admin_panel import admin
from api.delivery import delivery_api
from api.operator import operator_bp
from config import SQLALCHEMY_DATABASE_URI
from database.analytics import get_or_create_analytics_session, record_restaurant_visit
from database.extensions import db, migrate, socketio
import database.models
from database.db import get_session
from sqlalchemy import select
from database.models import RestaurantBranch

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("SESSION_COOKIE_SECURE")),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    SQLALCHEMY_DATABASE_URI=SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

db.init_app(app)
migrate.init_app(app, db, directory="migrations")
socketio.init_app(app, cors_allowed_origins="*")

app.register_blueprint(menu_api)
app.register_blueprint(delivery_api)
app.register_blueprint(admin)
app.register_blueprint(operator_bp)

@app.route("/")
def home():
    restaurants = get_active_restaurants()
    return render_template("client/landing.html", restaurants=restaurants)

@app.route("/cart")
def cart():
    return redirect(url_for("home"))

@app.route("/<restaurant_slug>")
def restaurant_home(restaurant_slug):
    restaurant = get_restaurant_by_slug_any_status(restaurant_slug)
    if not restaurant:
        abort(404)
    session_id = get_or_create_analytics_session(session)
    record_restaurant_visit(restaurant["id"], session_id, request.path)
    if not restaurant.get("is_active"):
        return render_template("client/restaurant_unavailable.html", restaurant=restaurant), 503

    db_session = get_session()
    branches = db_session.execute(
        select(RestaurantBranch)
        .where(RestaurantBranch.restaurant_id == restaurant["id"], RestaurantBranch.is_active.is_(True))
        .order_by(RestaurantBranch.name)
    ).scalars().all()

    if len(branches) == 1:
        return redirect(url_for("restaurant_branch_home", restaurant_slug=restaurant_slug, branch_public_id=branches[0].public_id))

    return render_template("client/branch_picker.html", restaurant=restaurant, branches=branches)


@app.route("/<restaurant_slug>/<branch_public_id>")
def restaurant_branch_home(restaurant_slug, branch_public_id):
    restaurant = get_restaurant_by_slug_any_status(restaurant_slug)
    if not restaurant:
        abort(404)
    if not restaurant.get("is_active"):
        return render_template("client/restaurant_unavailable.html", restaurant=restaurant), 503

    db_session = get_session()
    branch = db_session.execute(
        select(RestaurantBranch).where(
            RestaurantBranch.restaurant_id == restaurant["id"],
            RestaurantBranch.public_id == branch_public_id,
            RestaurantBranch.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if not branch:
        abort(404)

    return render_template("client/index.html", restaurant=restaurant, branch=branch)

@app.route("/<restaurant_slug>/<branch_public_id>/cart")
def restaurant_cart(restaurant_slug, branch_public_id):
    restaurant = get_restaurant_by_slug_any_status(restaurant_slug)
    if not restaurant:
        abort(404)
    if not restaurant.get("is_active"):
        return render_template("client/restaurant_unavailable.html", restaurant=restaurant), 503
    db_session = get_session()
    branch = db_session.execute(
        select(RestaurantBranch).where(
            RestaurantBranch.restaurant_id == restaurant["id"],
            RestaurantBranch.public_id == branch_public_id,
            RestaurantBranch.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if not branch:
        abort(404)
    return render_template("client/cart.html", restaurant=restaurant, branch=branch)

@app.errorhandler(404)
def page_not_found(error):
    return render_template("client/404.html"), 404

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

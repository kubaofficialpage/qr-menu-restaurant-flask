import os
from datetime import timedelta

from flask import Flask, abort, redirect, render_template, request, session, url_for
from dotenv import load_dotenv
from api.menu import get_active_restaurants, get_restaurant_by_slug, get_restaurant_by_slug_any_status, menu_api
from api.admin import admin
from database.analytics import get_or_create_analytics_session, record_restaurant_visit

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("SESSION_COOKIE_SECURE")),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

app.register_blueprint(menu_api)
app.register_blueprint(admin)

@app.route("/")
def home():
    restaurants = get_active_restaurants()
    return render_template("landing.html", restaurants=restaurants)

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
        return render_template("restaurant_unavailable.html", restaurant=restaurant), 503
    return render_template("index.html", restaurant=restaurant)

@app.route("/<restaurant_slug>/cart")
def restaurant_cart(restaurant_slug):
    restaurant = get_restaurant_by_slug_any_status(restaurant_slug)
    if not restaurant:
        abort(404)
    if not restaurant.get("is_active"):
        return render_template("restaurant_unavailable.html", restaurant=restaurant), 503
    return render_template("cart.html", restaurant=restaurant)

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

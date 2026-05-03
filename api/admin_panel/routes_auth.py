from flask import flash, redirect, render_template, request, session, url_for
from sqlalchemy import select
from werkzeug.security import check_password_hash

from database.db import get_session
from database.models import User

from . import admin
from .auth import rotate_csrf_token


@admin.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
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
    session.clear()
    return redirect(url_for("admin.login"))

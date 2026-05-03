import uuid
from functools import wraps

from flask import abort, redirect, request, session, url_for
from sqlalchemy import select

from database.db import get_session
from database.models import User


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    db_session = get_session()
    user = db_session.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    ).scalar_one_or_none()
    if not user:
        return None
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "global_role": user.global_role,
        "avatar": user.avatar,
    }


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

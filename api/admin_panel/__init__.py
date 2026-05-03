from flask import Blueprint, request

admin = Blueprint("admin", __name__, url_prefix="/admin")


@admin.before_request
def csrf_protect():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        from .auth import validate_csrf

        validate_csrf()

from . import auth  # noqa: E402,F401
from . import utils  # noqa: E402,F401
from . import queries  # noqa: E402,F401
from . import routes_context  # noqa: E402,F401
from . import routes_api  # noqa: E402,F401
from . import routes_auth  # noqa: E402,F401
from . import routes_dashboard  # noqa: E402,F401
from . import routes_qr  # noqa: E402,F401
from . import routes_menu_generator  # noqa: E402,F401
from . import routes_restaurants  # noqa: E402,F401
from . import routes_users  # noqa: E402,F401
from . import routes_menu  # noqa: E402,F401

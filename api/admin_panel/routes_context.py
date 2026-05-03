from . import admin
from .auth import current_user, get_csrf_token, is_developer
from .queries import get_accessible_restaurants, get_current_restaurant


@admin.context_processor
def inject_admin_context():
    return {
        "current_user": current_user(),
        "current_restaurant": get_current_restaurant(),
        "admin_restaurants": get_accessible_restaurants(),
        "is_developer": is_developer(),
        "csrf_token": get_csrf_token(),
    }

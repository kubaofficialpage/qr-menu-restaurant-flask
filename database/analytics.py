import uuid

from database.db import session_scope
from database.models import MenuCartEvent, RestaurantVisitEvent

ANALYTICS_SESSION_KEY = "analytics_session_id"


def get_or_create_analytics_session(session_obj):
    session_id = session_obj.get(ANALYTICS_SESSION_KEY)
    if not session_id:
        session_id = uuid.uuid4().hex
        session_obj[ANALYTICS_SESSION_KEY] = session_id
    return session_id


def record_restaurant_visit(restaurant_id, session_id, page_path=None):
    with session_scope() as db_session:
        db_session.add(
            RestaurantVisitEvent(
                restaurant_id=restaurant_id,
                session_id=session_id,
                page_path=page_path,
            )
        )


def record_menu_cart_add(restaurant_id, menu_item_id, session_id, quantity_delta=1):
    with session_scope() as db_session:
        db_session.add(
            MenuCartEvent(
                restaurant_id=restaurant_id,
                menu_item_id=menu_item_id,
                session_id=session_id,
                quantity_delta=quantity_delta,
            )
        )

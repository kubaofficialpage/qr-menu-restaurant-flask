import uuid

from database.db import get_db

ANALYTICS_SESSION_KEY = "analytics_session_id"


def get_or_create_analytics_session(session_obj):
    session_id = session_obj.get(ANALYTICS_SESSION_KEY)
    if not session_id:
        session_id = uuid.uuid4().hex
        session_obj[ANALYTICS_SESSION_KEY] = session_id
    return session_id


def record_restaurant_visit(restaurant_id, session_id, page_path=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO restaurant_visit_events (restaurant_id, session_id, page_path)
            VALUES (%s, %s, %s)
            """,
            (restaurant_id, session_id, page_path),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def record_menu_cart_add(restaurant_id, menu_item_id, session_id, quantity_delta=1):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO menu_cart_events (restaurant_id, menu_item_id, session_id, quantity_delta)
            VALUES (%s, %s, %s, %s)
            """,
            (restaurant_id, menu_item_id, session_id, quantity_delta),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

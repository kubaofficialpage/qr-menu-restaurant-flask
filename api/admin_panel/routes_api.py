from flask import jsonify, request

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from services.deepseek import generate_dish_description

from . import admin
from .auth import login_required
from .queries import require_restaurant


@admin.route("/api/menu/generate-description", methods=["POST"])
@login_required
def generate_menu_item_description():
    restaurant = require_restaurant()
    if not restaurant:
        return jsonify({"ok": False, "message": "Restaurant not selected"}), 400

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

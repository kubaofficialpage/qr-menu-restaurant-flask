import json
from typing import Any

import requests


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise RuntimeError("DeepSeek returned empty response")

    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 3:
            raw = "\n".join(lines[1:-1]).strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("DeepSeek did not return valid JSON")

    payload = raw[start:end + 1]
    return json.loads(payload)


def _sanitize_generated_menu(data: dict[str, Any]) -> dict[str, Any]:
    categories = []

    for category in data.get("categories", []):
        category_name = str(category.get("name") or "").strip()
        if not category_name:
            continue

        items = []
        for item in category.get("items", []):
            name = str(item.get("name") or "").strip()
            if not name:
                continue

            try:
                price = int(item.get("price") or 0)
            except (TypeError, ValueError):
                price = 0

            items.append(
                {
                    "name": name,
                    "description": str(item.get("description") or "").strip(),
                    "amount": str(item.get("amount") or "").strip() or None,
                    "price": max(price, 0),
                }
            )

        if items:
            categories.append({"name": category_name, "items": items})

    if not categories:
        raise RuntimeError("No categories or items were generated")

    return {"categories": categories}


def generate_menu_seed(
    *,
    api_key: str,
    base_url: str,
    model: str,
    restaurant_name: str,
    cuisine: str,
    concept: str,
    language: str = "ru",
    category_count: int = 5,
    items_per_category: int = 6,
    timeout_seconds: int = 40,
) -> dict[str, Any]:
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is not set")

    restaurant_name = (restaurant_name or "").strip()
    cuisine = (cuisine or "").strip()
    concept = (concept or "").strip()

    if not restaurant_name:
        raise ValueError("Restaurant name is required")
    if not cuisine:
        raise ValueError("Cuisine is required")
    if not concept:
        raise ValueError("Concept is required")

    system_prompt = (
        "Ты помощник для ресторанного бизнеса. "
        "Сгенерируй структуру меню для ресторана. "
        "Верни только JSON без markdown и без пояснений. "
        "Формат ответа: "
        '{"categories":[{"name":"Категория","items":[{"name":"Блюдо","description":"Описание","amount":"250 г","price":390}]}]}. '
        "Категории и блюда должны звучать реалистично, аппетитно и подходить для настоящего ресторана. "
        "Не повторяй блюда в нескольких категориях. "
        "Цена должна быть целым числом."
    )

    user_prompt = (
        f"Ресторан: {restaurant_name}\n"
        f"Кухня: {cuisine}\n"
        f"Концепция: {concept}\n"
        f"Язык: {language}\n"
        f"Количество категорий: {category_count}\n"
        f"Блюд в каждой категории: {items_per_category}\n"
        "Сделай категории и блюда разнообразными. "
        "Описание у каждого блюда 1-2 предложения. "
        "Укажи примерную порцию/объем в поле amount."
    )

    url = base_url.rstrip("/") + "/v1/chat/completions"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.8,
                "max_tokens": 2400,
            }
        ),
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("DeepSeek returned unexpected response") from exc

    parsed = _extract_json_object(str(content))
    return _sanitize_generated_menu(parsed)

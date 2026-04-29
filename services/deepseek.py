import json
from typing import Optional

import requests


def generate_dish_description(
    *,
    api_key: str,
    base_url: str,
    model: str,
    dish_name: str,
    language: str = "ru",
    timeout_seconds: int = 20,
) -> str:
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is not set")

    dish_name = (dish_name or "").strip()
    if not dish_name:
        raise ValueError("Dish name is required")

    system_prompt = (
        "Ты — помощник для ресторана. "
        "Сгенерируй короткое, аппетитное и правдоподобное описание блюда. "
        "Не выдумывай конкретные бренды. Не добавляй аллергенные предупреждения. "
        "Верни только текст описания без кавычек и без markdown."
    )

    user_prompt = (
        f"Название блюда: {dish_name}.\n"
        f"Язык: {language}.\n"
        "Сделай 1-3 предложения, нейтральный маркетинговый тон."
    )

    url = base_url.rstrip("/") + "/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 180,
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout_seconds)
    response.raise_for_status()
    data = response.json()

    content: Optional[str] = None
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = None

    if not content or not str(content).strip():
        raise RuntimeError("DeepSeek returned empty response")

    return str(content).strip()

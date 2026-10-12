"""🧠 Розумник: питає Gemini, чи варто публікувати новину."""
import json
import os
import time
from typing import Optional

import requests

# Основна модель + запасні. Змінити: GEMINI_MODEL="модель1,модель2"
# Назви моделей Google оновлює, тож за потреби підставте актуальні.
MODELS = os.environ.get(
    "GEMINI_MODEL", "gemini-3.1-flash-lite,gemini-3.6-flash"
).split(",")
RETRIES = 3  # спроб на кожну модель


def _url(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model.strip()}:generateContent"


def judge(item: dict, criteria: str, recent: Optional[list] = None) -> dict:
    """Повертає {"publish": bool, "summary": str}. При збої додає error=True."""
    recent_block = "\n".join(f"- {s}" for s in (recent or [])[-15:]) or "— (поки нічого)"
    prompt = f"""{criteria}

Нещодавно вже опубліковано. Якщо новина про ту саму подію, став publish=false:
{recent_block}

Оціни новину нижче.
Відповідай ТІЛЬКИ JSON такого вигляду:
{{"publish": true або false, "summary": "короткий переказ українською, 2-3 речення, своїми словами"}}
Якщо publish=false, summary може бути порожнім.

Джерело: {item['source']}
Текст: {item['text'][:3000]}
"""
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }
    headers = {"x-goog-api-key": os.environ["AI_API_KEY"]}

    for model in MODELS:
        for attempt in range(1, RETRIES + 1):
            try:
                r = requests.post(_url(model), headers=headers, json=body, timeout=60)
                if r.status_code in (429, 500, 503):
                    wait = 5 * attempt
                    print(f"[~] {model}: {r.status_code}, чекаю {wait}с (спроба {attempt}/{RETRIES})")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                data = json.loads(raw)
                return {
                    "publish": bool(data.get("publish")),
                    "summary": str(data.get("summary", "")).strip(),
                }
            except Exception as err:
                print(f"[!] {model}: {err}")
                break  # не тимчасова помилка: переходимо до запасної моделі

    return {"publish": False, "summary": "", "error": True}

"""🧠 Розумник: питає Gemini, чи варто публікувати новину."""
import json
import os

import requests

# Модель можна змінити через змінну середовища, якщо Google оновить назви.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite,gemini-3.6-flash")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def judge(item: dict, criteria: str) -> dict:
    """Повертає {"publish": bool, "summary": str}. При помилці — publish=False."""
    prompt = f"""{criteria}

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
    try:
        r = requests.post(
            URL,
            headers={"x-goog-api-key": os.environ["AI_API_KEY"]},
            json=body,
            timeout=60,
        )
        r.raise_for_status()
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(raw)
        return {
            "publish": bool(data.get("publish")),
            "summary": str(data.get("summary", "")).strip(),
        }
    except Exception as err:
        print(f"[!] Gemini: {err}")
        return {"publish": False, "summary": "", "error": True}

"""📣 Голосник: публікує пост через Telegram Bot API (з фото, якщо воно є)."""
import html
import os
from typing import Optional

import requests

CAPTION_LIMIT = 1024  # ліміт Telegram для підпису під фото


def _api(method: str) -> str:
    token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    return f"https://api.telegram.org/bot{token}/{method}"


def post_to_telegram(summary: str, link: str, source: str,
                     image: Optional[str] = None) -> None:
    text = (
        f"{html.escape(summary)}\n\n"
        f'🔗 <a href="{html.escape(link, quote=True)}">{html.escape(source)}</a>'
    )
    chat_id = os.environ["TELEGRAM_CHANNEL_ID"].strip()

    # 🖼 Спершу пробуємо з фото: фото зверху, текст як підпис
    if image and len(text) <= CAPTION_LIMIT:
        r = requests.post(
            _api("sendPhoto"),
            json={
                "chat_id": chat_id,
                "photo": image,
                "caption": text,
                "parse_mode": "HTML",
            },
            timeout=30,
        )
        if r.ok:
            return
        print(f"[~] фото не вдалося ({r.status_code} {r.text[:150]}), публікую без фото")

    # 📝 Без фото (або якщо фото не вийшло)
    r = requests.post(
        _api("sendMessage"),
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        },
        timeout=30,
    )
    if not r.ok:
        # Telegram пояснює причину в тілі відповіді — показуємо її в лозі
        raise RuntimeError(f"{r.status_code} {r.text}")

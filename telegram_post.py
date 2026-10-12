"""📣 Голосник: публікує пост через Telegram Bot API."""
import html
import os

import requests


def post_to_telegram(summary: str, link: str, source: str) -> None:
    text = (
        f"{html.escape(summary)}\n\n"
        f'🔗 <a href="{html.escape(link, quote=True)}">{html.escape(source)}</a>'
    )
    token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    chat_id = os.environ["TELEGRAM_CHANNEL_ID"].strip()
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
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

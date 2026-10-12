"""📣 Голосник: публікує пост через Telegram Bot API."""
import html
import os

import requests


def post_to_telegram(summary: str, link: str, source: str) -> None:
    text = (
        f"{html.escape(summary)}\n\n"
        f'🔗 <a href="{html.escape(link, quote=True)}">Джерело: {html.escape(source)}</a>'
    )
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": os.environ["TELEGRAM_CHANNEL_ID"],
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    r.raise_for_status()

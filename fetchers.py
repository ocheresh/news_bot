"""📬 Листоноша: збирає новини і приводить їх до єдиного формату.

Формат новини: {"source", "text", "link", "date"}  (date — datetime UTC або None)
"""
import calendar
import re
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; news-bot/1.0)"}


def _clean(html: str) -> str:
    text = BeautifulSoup(html or "", "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def fetch_rss(url: str) -> list:
    r = requests.get(url, headers=HEADERS, timeout=20)
    feed = feedparser.parse(r.content)
    if not feed.entries:
        print(f"  [!] {url}: HTTP {r.status_code}, "
              f"тип {r.headers.get('content-type')}, записів немає "
              f"({feed.get('bozo_exception')})")
    items = []
    for e in feed.entries:
        date = None
        if getattr(e, "published_parsed", None):
            date = datetime.fromtimestamp(
                calendar.timegm(e.published_parsed), tz=timezone.utc
            )
        title = _clean(e.get("title", ""))
        body = _clean(e.get("summary", ""))
        items.append({
            "source": feed.feed.get("title", url),
            "text": f"{title}. {body}".strip(". "),
            "link": e.get("link", ""),
            "date": date,
        })
    return items


def fetch_tg_public(channel: str) -> list[dict]:
    """Читає публічний канал через веб-превʼю t.me/s/<канал>."""
    r = requests.get(f"https://t.me/s/{channel}", headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for msg in soup.select("div.tgme_widget_message"):
        post_id = msg.get("data-post")  # напр. "channel/12345"
        text_div = msg.select_one("div.tgme_widget_message_text")
        if not post_id or not text_div:
            continue  # пости без тексту (тільки фото тощо) пропускаємо
        time_tag = msg.select_one("a.tgme_widget_message_date time")
        date = None
        if time_tag and time_tag.get("datetime"):
            date = datetime.fromisoformat(time_tag["datetime"]).astimezone(timezone.utc)
        items.append({
            "source": f"@{channel}",
            "text": _clean(text_div.get_text(" ")),
            "link": f"https://t.me/{post_id}",
            "date": date,
        })
    return items


def fetch_all(rss_feeds: list, tg_channels: list) -> list:
    all_items = []
    for url in rss_feeds:
        try:
            got = fetch_rss(url)
            print(f"  RSS {url}: {len(got)}")
            all_items += got
        except Exception as err:  # один зламаний сайт не має валити весь запуск
            print(f"[!] RSS {url}: {err}")
    for ch in tg_channels:
        try:
            got = fetch_tg_public(ch)
            print(f"  Telegram @{ch}: {len(got)}")
            all_items += got
        except Exception as err:
            print(f"[!] Telegram @{ch}: {err}")
    return all_items

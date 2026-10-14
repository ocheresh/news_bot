"""📬 Листоноша: збирає новини і приводить їх до єдиного формату.

Формат новини: {"source", "text", "link", "date", "image"}
(date — datetime UTC або None; image — адреса фото або None)
"""
import calendar
import re
import warnings
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
    "Accept-Language": "uk-UA,uk;q=0.9",
}


def _clean(html: str) -> str:
    text = BeautifulSoup(html or "", "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def _rss_image(entry):
    """Шукає фото в записі RSS: media-теги, вкладення, перший <img> у тексті."""
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key, []) or []:
            if m.get("url"):
                return m["url"]
    for enc in entry.get("enclosures", []) or []:
        if str(enc.get("type", "")).startswith("image") and enc.get("href"):
            return enc["href"]
    html = entry.get("summary", "")
    if not html and entry.get("content"):
        html = entry["content"][0].get("value", "")
    img = BeautifulSoup(html or "", "html.parser").find("img")
    if img and img.get("src", "").startswith("http"):
        return img["src"]
    return None


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
            "image": _rss_image(e),
        })
    return items


def _tg_image(msg):
    """Фото з поста в публічному превʼю Telegram (перше, якщо їх кілька)."""
    wrap = msg.select_one("a.tgme_widget_message_photo_wrap")
    if wrap:
        m = re.search(r"url\(['\"]?([^'\")]+)['\"]?\)", wrap.get("style", ""))
        if m:
            return m.group(1)
    return None


def fetch_tg_public(channel: str) -> list:
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
            "image": _tg_image(msg),
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

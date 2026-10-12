"""Головний: керує всіма роботами по черзі.

Локальний тест без публікації:  DRY_RUN=1 python main.py
"""
import os
import time
from datetime import datetime, timedelta, timezone

from ai_filter import judge
from fetchers import fetch_all
from seen import load_seen, save_seen
from sources import (CRITERIA, MAX_AGE_HOURS, MAX_AI_CALLS, MAX_POSTS,
                     RSS_FEEDS, TG_CHANNELS)
from telegram_post import post_to_telegram

DRY_RUN = os.environ.get("DRY_RUN") == "1"
AI_PAUSE_SECONDS = 7  # безкоштовний ліміт Gemini — кілька запитів на хвилину


def main() -> None:
    seen = load_seen()
    seen_set = set(seen)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)

    # 📬 1. Листоноша
    items = fetch_all(RSS_FEEDS, TG_CHANNELS)
    print(f"Зібрано новин: {len(items)}")

    # 🧹 2. Вахтер: нові + свіжі
    fresh = []
    for it in items:
        key = it["link"] or it["text"][:200]
        if key in seen_set:
            continue
        if it["date"] and it["date"] < cutoff:
            seen.append(key)  # стара — більше не повертаємось
            seen_set.add(key)
            continue
        it["key"] = key
        fresh.append(it)
    print(f"Нових і свіжих: {len(fresh)}")

    posted = 0
    ai_calls = 0
    for it in fresh:
        if ai_calls >= MAX_AI_CALLS or posted >= MAX_POSTS:
            break  # решта лишається «не баченою» і дочекається наступного запуску

        # 🧠 3. Розумник
        verdict = judge(it, CRITERIA)
        ai_calls += 1
        time.sleep(AI_PAUSE_SECONDS)
        if verdict.get("error"):
            continue  # збій ШІ: не позначаємо як бачену, спробуємо пізніше

        # 📣 4. Голосник
        if verdict["publish"] and verdict["summary"]:
            if DRY_RUN:
                print(f"\n[DRY] {verdict['summary']}\n      {it['link']}\n")
            else:
                try:
                    post_to_telegram(verdict["summary"], it["link"], it["source"])
                except Exception as err:
                    print(f"[!] Telegram: {err}")
                    continue  # не вдалося опублікувати — спробуємо наступного разу
            posted += 1

        # 📓 5. Писар: запамʼятовуємо, що новину вже розглянули
        seen.append(it["key"])
        seen_set.add(it["key"])

    save_seen(seen)
    print(f"Опубліковано: {posted}, запитів до ШІ: {ai_calls}")


if __name__ == "__main__":
    main()

"""Головний: керує всіма роботами по черзі.

Тест без публікації і без запису в seen.json:  DRY_RUN=1 python main.py
"""
import os
import time
from datetime import datetime, timedelta, timezone

from ai_filter import judge
from fetchers import fetch_all
from seen import load_recent, load_seen, save_recent, save_seen
from sources import (CRITERIA, MAX_AGE_HOURS, MAX_AI_CALLS, MAX_PER_SOURCE,
                     MAX_POSTS, RSS_FEEDS, TG_CHANNELS)
from telegram_post import post_to_telegram

DRY_RUN = os.environ.get("DRY_RUN") == "1"
AI_PAUSE_SECONDS = 7  # пауза між запитами до безкоштовного Gemini
MAX_RUNTIME_SECONDS = 8 * 60  # після цього нові запити до ШІ не починаємо


def main() -> None:
    started = time.time()
    seen = load_seen()
    seen_set = set(seen)
    recent = load_recent()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)

    # 📬 1. Листоноша
    items = fetch_all(RSS_FEEDS, TG_CHANNELS)
    print(f"Зібрано новин: {len(items)}")

    # 🧹 2. Вахтер: нові, свіжі, без повторів
    fresh = []
    in_run = set()
    for it in items:
        key = it["link"] or it["text"][:200]
        if key in seen_set or key in in_run:
            continue
        if it["date"] and it["date"] < cutoff:
            seen.append(key)  # стара: більше не повертаємось
            seen_set.add(key)
            continue
        it["key"] = key
        in_run.add(key)
        fresh.append(it)

    # найновіші першими
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    fresh.sort(key=lambda it: it["date"] or epoch, reverse=True)
    print(f"Нових і свіжих: {len(fresh)}")

    posted = 0
    ai_calls = 0
    per_source = {}

    for it in fresh:
        if ai_calls >= MAX_AI_CALLS or posted >= MAX_POSTS:
            break
        if time.time() - started > MAX_RUNTIME_SECONDS:
            print("Ліміт часу запуску: решта новин дочекається наступного разу")
            break
        if per_source.get(it["source"], 0) >= MAX_PER_SOURCE:
            continue  # з цього джерела вже є пост; новина дочекається наступного запуску

        # 🧠 3. Розумник
        verdict = judge(it, CRITERIA, recent)
        ai_calls += 1
        mark = "✅" if verdict["publish"] else ("⚠️" if verdict.get("error") else "❌")
        print(f"[{ai_calls}/{MAX_AI_CALLS}] {mark} {it['source']}: {it['text'][:80]}")
        time.sleep(AI_PAUSE_SECONDS)
        if verdict.get("error"):
            continue  # збій ШІ: не позначаємо як оброблену

        # 📣 4. Голосник
        if verdict["publish"] and verdict["summary"]:
            if DRY_RUN:
                print(f"\n[DRY] {verdict['summary']}\n      {it['link']}\n")
            else:
                try:
                    post_to_telegram(verdict["summary"], it["link"], it["source"], it.get("image"))
                except Exception as err:
                    print(f"[!] Telegram: {err}")
                    continue  # не вдалося опублікувати: спробуємо наступного разу
            posted += 1
            per_source[it["source"]] = per_source.get(it["source"], 0) + 1
            recent.append(verdict["summary"])

        # 📓 5. Писар
        seen.append(it["key"])
        seen_set.add(it["key"])

    if DRY_RUN:
        print("DRY_RUN: seen.json і recent.json не змінено")
    else:
        save_seen(seen)
        save_recent(recent)
    print(f"Опубліковано: {posted}, запитів до ШІ: {ai_calls}")


if __name__ == "__main__":
    main()

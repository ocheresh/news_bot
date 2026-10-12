"""🧹 Вахтер + 📓 Писар: памʼятає, що вже оброблено (seen.json)
і що нещодавно опубліковано (recent.json)."""
import json
from pathlib import Path

SEEN_FILE = Path("seen.json")
RECENT_FILE = Path("recent.json")
MAX_SEEN = 5000   # щоб файл не ріс безкінечно
MAX_RECENT = 30


def _load(path: Path) -> list:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def _save(path: Path, data: list, keep: int) -> None:
    path.write_text(
        json.dumps(data[-keep:], ensure_ascii=False, indent=0),
        encoding="utf-8",
    )


def load_seen() -> list:
    return _load(SEEN_FILE)


def save_seen(seen: list) -> None:
    _save(SEEN_FILE, seen, MAX_SEEN)


def load_recent() -> list:
    return _load(RECENT_FILE)


def save_recent(recent: list) -> None:
    _save(RECENT_FILE, recent, MAX_RECENT)

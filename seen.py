"""🧹 Вахтер + 📓 Писар: памʼятає, які новини вже оброблені (seen.json)."""
import json
from pathlib import Path

SEEN_FILE = Path("seen.json")
MAX_KEEP = 5000  # щоб файл не ріс безкінечно


def load_seen() -> list[str]:
    if SEEN_FILE.exists():
        try:
            return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def save_seen(seen: list[str]) -> None:
    SEEN_FILE.write_text(
        json.dumps(seen[-MAX_KEEP:], ensure_ascii=False, indent=0),
        encoding="utf-8",
    )

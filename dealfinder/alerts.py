"""Remembers which deals were already emailed, so only new ones are sent."""
import json
from datetime import date, timedelta
from pathlib import Path

REALERT_DAYS = 30  # a deal emailed longer ago than this can be emailed again
KEEP_DAYS = 90     # forget sent alerts older than this


def load_sent(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_sent(path: Path, sent: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(sent, indent=1, sort_keys=True), encoding="utf-8")


def new_alerts(alerts: list[dict], sent: dict, today: date) -> list[dict]:
    """Alerts never emailed, cheaper than when last emailed, or last emailed over 30 days ago."""
    cutoff = (today - timedelta(days=REALERT_DAYS)).isoformat()
    fresh = []
    for item in alerts:
        before = sent.get(item["id"])
        if before is None or item["price"] < before["price"] or before["date"] < cutoff:
            fresh.append(item)
    return fresh


def remember(alerts: list[dict], sent: dict, today: date) -> dict:
    cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
    updated = {item_id: entry for item_id, entry in sent.items() if entry["date"] >= cutoff}
    for item in alerts:
        updated[item["id"]] = {"price": item["price"], "date": today.isoformat()}
    return updated

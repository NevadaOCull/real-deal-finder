import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .models import Observation


@dataclass
class PricePoint:
    date: str  # YYYY-MM-DD
    price: float | None  # None = couldn't check that day


class History:
    """One JSON file per item holding one price per day."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def _path(self, item_id: str) -> Path:
        return self.folder / (re.sub(r"[^A-Za-z0-9_.-]", "_", item_id) + ".json")

    def load(self, item_id: str) -> list[PricePoint]:
        path = self._path(item_id)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [PricePoint(p["date"], p["price"]) for p in data.get("points", [])]

    def record(self, obs: Observation, today: date) -> list[PricePoint]:
        points = self.load(obs.id)
        day = today.isoformat()
        if points and points[-1].date == day:
            old = points[-1].price
            if obs.price is not None and (old is None or obs.price < old):
                points[-1] = PricePoint(day, obs.price)
        else:
            points.append(PricePoint(day, obs.price))
        self.folder.mkdir(parents=True, exist_ok=True)
        self._path(obs.id).write_text(json.dumps({
            "id": obs.id,
            "title": obs.title,
            "store": obs.store,
            "url": obs.url,
            "points": [{"date": p.date, "price": p.price} for p in points],
        }, indent=1), encoding="utf-8")
        return points

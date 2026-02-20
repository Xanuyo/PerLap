import json
import os
from datetime import datetime
from typing import Optional

from .events import LapEvent, EventType

RACES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "races")


class RaceLog:

    def __init__(self):
        self._active = False
        self._race_id: str = ""
        self._start_time: str = ""
        self._events: list[dict] = []
        self._car_laps: dict[int, list[dict]] = {}
        self._car_names: dict[int, str] = {}
        self._last_crossing_ms: dict[int, int] = {}

    @property
    def active(self) -> bool:
        return self._active

    def start_race(self, car_names: dict[int, str]):
        now = datetime.now()
        self._race_id = now.strftime("%Y-%m-%d_%H-%M-%S")
        self._start_time = now.isoformat()
        self._events = []
        self._car_laps = {}
        self._car_names = dict(car_names)
        self._last_crossing_ms = {}
        self._active = True

        for car_id in car_names:
            self._car_laps[car_id] = []

    def record_event(self, event: LapEvent):
        if not self._active:
            return

        self._events.append(event.to_dict())

        if event.event == EventType.LAP:
            leader_ts = self._find_leader_timestamp(event.lap_number)
            gap = event.timestamp_ms - leader_ts if leader_ts > 0 else 0

            self._car_laps.setdefault(event.car_id, []).append({
                "lap": event.lap_number,
                "time_ms": event.lap_time_ms,
                "timestamp_ms": event.timestamp_ms,
                "gap_to_leader_ms": gap,
            })
            self._last_crossing_ms[event.car_id] = event.timestamp_ms

    def _find_leader_timestamp(self, lap_number: int) -> int:
        earliest = 0
        for car_id, laps in self._car_laps.items():
            for lap in laps:
                if lap["lap"] == lap_number:
                    if earliest == 0 or lap["timestamp_ms"] < earliest:
                        earliest = lap["timestamp_ms"]
                    break
        return earliest

    def end_race(self) -> Optional[str]:
        if not self._active:
            return None
        self._active = False

        last_event_ms = max((e["timestamp_ms"] for e in self._events), default=0)

        cars_data = []
        for car_id, laps in self._car_laps.items():
            times = [l["time_ms"] for l in laps]
            cars_data.append({
                "id": car_id,
                "name": self._car_names.get(car_id, f"Auto {car_id}"),
                "laps": laps,
                "total_laps": len(laps),
                "best_lap_ms": min(times) if times else 0,
                "avg_lap_ms": sum(times) // len(times) if times else 0,
            })

        race_data = {
            "id": self._race_id,
            "date": self._start_time,
            "duration_ms": last_event_ms,
            "cars": cars_data,
            "events": self._events,
        }

        os.makedirs(RACES_DIR, exist_ok=True)
        path = os.path.join(RACES_DIR, f"{self._race_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(race_data, f, indent=2, ensure_ascii=False)

        return path

    @staticmethod
    def load_race(path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def list_races() -> list[str]:
        os.makedirs(RACES_DIR, exist_ok=True)
        files = [f for f in os.listdir(RACES_DIR) if f.endswith(".json")]
        files.sort(reverse=True)
        return [os.path.join(RACES_DIR, f) for f in files]

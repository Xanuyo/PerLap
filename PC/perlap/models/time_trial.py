import json
import os
import time
from datetime import datetime
from typing import Optional

from .events import LapEvent, EventType

RANKING_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ranking.json"
)

DEFAULT_TOTAL_LAPS = 5
MIN_LAP_MS = 2000


class TimeTrial:

    def __init__(self, total_laps: int = DEFAULT_TOTAL_LAPS):
        self.total_laps = total_laps
        self._start_time: float = 0
        self._last_crossing_ms: int = 0
        self._lap_times: list[int] = []
        self._started = False
        self._finished = False
        self._best_lap_ms: int = 999999

    @property
    def started(self) -> bool:
        return self._started

    @property
    def finished(self) -> bool:
        return self._finished

    @property
    def current_lap(self) -> int:
        return len(self._lap_times)

    @property
    def lap_times(self) -> list[int]:
        return list(self._lap_times)

    @property
    def total_time_ms(self) -> int:
        return sum(self._lap_times)

    @property
    def best_lap_ms(self) -> int:
        return self._best_lap_ms if self._best_lap_ms < 999999 else 0

    def _now_ms(self) -> int:
        return int((time.perf_counter() - self._start_time) * 1000)

    def reset(self):
        self._start_time = time.perf_counter()
        self._last_crossing_ms = 0
        self._lap_times.clear()
        self._started = False
        self._finished = False
        self._best_lap_ms = 999999

    def process_crossing(self, car_id: int = 0, source: str = "CAMERA") -> Optional[LapEvent]:
        if self._finished:
            return None

        now = self._now_ms()

        if not self._started:
            self._started = True
            self._last_crossing_ms = now
            return LapEvent(
                event=EventType.START,
                timestamp_ms=now,
                car_id=car_id,
                car_name="",
                source=source,
            )

        elapsed = now - self._last_crossing_ms
        if elapsed < MIN_LAP_MS:
            return None

        self._lap_times.append(elapsed)
        self._last_crossing_ms = now
        if elapsed < self._best_lap_ms:
            self._best_lap_ms = elapsed

        lap_num = len(self._lap_times)

        if lap_num >= self.total_laps:
            self._finished = True

        return LapEvent(
            event=EventType.LAP,
            timestamp_ms=now,
            car_id=car_id,
            car_name="",
            lap_number=lap_num,
            lap_time_ms=elapsed,
            best_lap_ms=self._best_lap_ms,
            source=source,
        )

    # --- Ranking ---

    @staticmethod
    def load_ranking() -> list[dict]:
        if not os.path.exists(RANKING_PATH):
            return []
        try:
            with open(RANKING_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def save_ranking(ranking: list[dict]):
        with open(RANKING_PATH, "w", encoding="utf-8") as f:
            json.dump(ranking, f, indent=2, ensure_ascii=False)

    def submit_to_ranking(self, player_name: str) -> dict:
        entry = {
            "player": player_name,
            "total_ms": self.total_time_ms,
            "laps": self.total_laps,
            "lap_times_ms": list(self._lap_times),
            "best_lap_ms": self.best_lap_ms,
            "date": datetime.now().isoformat(),
        }

        ranking = self.load_ranking()
        ranking.append(entry)
        ranking.sort(key=lambda x: x["total_ms"])
        self.save_ranking(ranking)

        position = next(i for i, r in enumerate(ranking) if r is entry) + 1
        entry["position"] = position
        return entry

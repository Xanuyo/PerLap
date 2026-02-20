import time
from typing import Optional

from .car import CarColor, CarState
from .events import LapEvent, EventType

MAX_CARS = 6
MIN_LAP_MS = 2000


class RaceManager:

    def __init__(self):
        self.cars: list[CarColor] = [CarColor() for _ in range(MAX_CARS)]
        self.states: list[CarState] = [CarState() for _ in range(MAX_CARS)]
        self._start_time: float = time.perf_counter()

    def _now_ms(self) -> int:
        return int((time.perf_counter() - self._start_time) * 1000)

    def register_car(self, slot: int, name: str, hsv_lower, hsv_upper,
                     display_color: tuple) -> Optional[LapEvent]:
        if not 0 <= slot < MAX_CARS:
            return None
        self.cars[slot] = CarColor(
            name=name,
            hsv_lower=hsv_lower,
            hsv_upper=hsv_upper,
            display_color=display_color,
            active=True,
        )
        self.states[slot].reset()
        return None

    def process_crossing(self, car_id: int, source: str = "CAMERA") -> Optional[LapEvent]:
        if not 0 <= car_id < MAX_CARS:
            return None
        if not self.cars[car_id].active:
            return None

        car = self.cars[car_id]
        cs = self.states[car_id]
        now = self._now_ms()

        if not cs.started:
            cs.started = True
            cs.last_lap_time_ms = now
            cs.lap_count = 0
            return LapEvent(
                event=EventType.START,
                timestamp_ms=now,
                car_id=car_id,
                car_name=car.name,
                source=source,
            )

        elapsed = now - cs.last_lap_time_ms
        if elapsed < MIN_LAP_MS:
            return None

        cs.lap_count += 1
        cs.last_lap_time_ms = now
        cs.lap_times.append(elapsed)
        if elapsed < cs.best_lap_ms:
            cs.best_lap_ms = elapsed

        return LapEvent(
            event=EventType.LAP,
            timestamp_ms=now,
            car_id=car_id,
            car_name=car.name,
            lap_number=cs.lap_count,
            lap_time_ms=elapsed,
            best_lap_ms=cs.best_lap_ms,
            source=source,
        )

    def reset(self) -> LapEvent:
        for s in self.states:
            s.reset()
        self._start_time = time.perf_counter()
        return LapEvent(
            event=EventType.RESET,
            timestamp_ms=0,
            car_id=-1,
            car_name="",
        )

    def get_standings(self) -> list[dict]:
        standings = []
        for i in range(MAX_CARS):
            if not self.cars[i].active:
                continue
            cs = self.states[i]
            avg = 0
            if cs.lap_times:
                avg = sum(cs.lap_times) // len(cs.lap_times)
            standings.append({
                "id": i,
                "name": self.cars[i].name,
                "laps": cs.lap_count,
                "best_ms": cs.best_lap_ms if cs.best_lap_ms < 999999 else 0,
                "last_ms": cs.lap_times[-1] if cs.lap_times else 0,
                "avg_ms": avg,
                "started": cs.started,
                "color": self.cars[i].display_color,
            })
        standings.sort(key=lambda x: (-x["laps"], x["best_ms"]))
        return standings

    def get_active_cars(self) -> list[tuple[int, CarColor]]:
        return [(i, c) for i, c in enumerate(self.cars) if c.active]

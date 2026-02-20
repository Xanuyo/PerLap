from enum import Enum
from dataclasses import dataclass


class EventType(Enum):
    READY = "READY"
    START = "START"
    LAP = "LAP"
    RESET = "RESET"
    STATUS = "STATUS"
    ERROR = "ERROR"


@dataclass
class LapEvent:
    event: EventType
    timestamp_ms: int
    car_id: int
    car_name: str
    lap_number: int = 0
    lap_time_ms: int = 0
    best_lap_ms: int = 0
    source: str = "CAMERA"

    def to_dict(self) -> dict:
        return {
            "event": self.event.value,
            "timestamp_ms": self.timestamp_ms,
            "car": self.car_name,
            "car_id": self.car_id,
            "lap": self.lap_number,
            "time_ms": self.lap_time_ms,
            "best_ms": self.best_lap_ms,
            "source": self.source,
        }

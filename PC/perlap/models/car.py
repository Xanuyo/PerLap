from dataclasses import dataclass, field

import numpy as np


@dataclass
class CarColor:
    name: str = ""
    hsv_lower: np.ndarray = field(default_factory=lambda: np.array([0, 0, 0]))
    hsv_upper: np.ndarray = field(default_factory=lambda: np.array([180, 255, 255]))
    display_color: tuple = (255, 255, 255)  # BGR for UI
    active: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "hsv_lower": self.hsv_lower.tolist(),
            "hsv_upper": self.hsv_upper.tolist(),
            "display_color": list(self.display_color),
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CarColor":
        return cls(
            name=d["name"],
            hsv_lower=np.array(d["hsv_lower"]),
            hsv_upper=np.array(d["hsv_upper"]),
            display_color=tuple(d["display_color"]),
            active=d["active"],
        )


@dataclass
class CarState:
    last_lap_time_ms: int = 0
    lap_count: int = 0
    started: bool = False
    best_lap_ms: int = 999999
    lap_times: list = field(default_factory=list)

    def reset(self):
        self.last_lap_time_ms = 0
        self.lap_count = 0
        self.started = False
        self.best_lap_ms = 999999
        self.lap_times.clear()

import numpy as np


class FinishLine:

    def __init__(self, p1: tuple[int, int] = (0, 0), p2: tuple[int, int] = (0, 0)):
        self.p1 = np.array(p1, dtype=float)
        self.p2 = np.array(p2, dtype=float)

    @property
    def defined(self) -> bool:
        return not (np.array_equal(self.p1, self.p2))

    def get_detection_band(self, frame_h: int, frame_w: int, band_width: int = 120) -> tuple:
        if not self.defined:
            return 0, 0, frame_w, frame_h
        y_center = (self.p1[1] + self.p2[1]) / 2
        y_min = max(0, int(y_center - band_width))
        y_max = min(frame_h, int(y_center + band_width))
        x_min = max(0, int(min(self.p1[0], self.p2[0])) - 10)
        x_max = min(frame_w, int(max(self.p1[0], self.p2[0])) + 10)
        return x_min, y_min, x_max, y_max

    def get_roi_bounds(self, frame_h: int, frame_w: int, margin: int = 60) -> tuple:
        if not self.defined:
            return 0, 0, frame_w, frame_h
        y_min = max(0, int(min(self.p1[1], self.p2[1])) - margin)
        y_max = min(frame_h, int(max(self.p1[1], self.p2[1])) + margin)
        x_min = max(0, int(min(self.p1[0], self.p2[0])) - margin)
        x_max = min(frame_w, int(max(self.p1[0], self.p2[0])) + margin)
        return x_min, y_min, x_max, y_max

    def to_dict(self) -> dict:
        return {"p1": self.p1.tolist(), "p2": self.p2.tolist()}

    @classmethod
    def from_dict(cls, d: dict) -> "FinishLine":
        return cls(tuple(d["p1"]), tuple(d["p2"]))

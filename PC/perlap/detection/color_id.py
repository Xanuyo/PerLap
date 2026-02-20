import cv2
import numpy as np

# Presets: (margin_h, margin_s, margin_v, min_s, min_v)
SENSITIVITY_PRESETS = {
    "Estricto":  (10, 40, 40, 60, 60),
    "Normal":    (15, 60, 60, 40, 40),
    "Amplio":    (20, 80, 80, 30, 30),
    "Muy amplio": (25, 100, 100, 20, 20),
}

DEFAULT_SENSITIVITY = "Normal"


class ColorCalibrator:

    _sensitivity = DEFAULT_SENSITIVITY

    @classmethod
    def set_sensitivity(cls, name: str):
        if name in SENSITIVITY_PRESETS:
            cls._sensitivity = name

    @classmethod
    def get_sensitivity(cls) -> str:
        return cls._sensitivity

    @staticmethod
    def sample_color(frame_bgr: np.ndarray, center: tuple[int, int],
                     patch_size: int = 20,
                     sensitivity: str = None) -> tuple[np.ndarray, np.ndarray, tuple]:
        cx, cy = center
        r = patch_size // 2
        h, w = frame_bgr.shape[:2]
        y1 = max(0, cy - r)
        y2 = min(h, cy + r)
        x1 = max(0, cx - r)
        x2 = min(w, cx + r)

        patch = frame_bgr[y1:y2, x1:x2]
        hsv_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)

        mean_hsv = hsv_patch.mean(axis=(0, 1))

        preset_name = sensitivity or ColorCalibrator._sensitivity
        mh, ms, mv, min_s, min_v = SENSITIVITY_PRESETS.get(
            preset_name, SENSITIVITY_PRESETS[DEFAULT_SENSITIVITY]
        )

        lower = np.array([
            max(0, mean_hsv[0] - mh),
            max(min_s, mean_hsv[1] - ms),
            max(min_v, mean_hsv[2] - mv),
        ], dtype=np.uint8)
        upper = np.array([
            min(180, mean_hsv[0] + mh),
            min(255, mean_hsv[1] + ms),
            min(255, mean_hsv[2] + mv),
        ], dtype=np.uint8)

        mean_bgr = patch.mean(axis=(0, 1)).astype(int)
        display_color = (int(mean_bgr[0]), int(mean_bgr[1]), int(mean_bgr[2]))

        return lower, upper, display_color

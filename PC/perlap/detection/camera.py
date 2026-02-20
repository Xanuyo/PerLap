import time

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from ..models.car import CarColor
from .finish_line import FinishLine

DEFAULT_MIN_PIXEL_COUNT = 80
CROSSING_COOLDOWN_S = 1.5  # seconds between detections per car


class CameraSource(QThread):
    frame_ready = Signal(QImage)
    crossing_detected = Signal(int)  # car_id

    def __init__(self, device_index: int = 0, parent=None):
        super().__init__(parent)
        self.device_index = device_index
        self._running = False
        self._car_entries: list[tuple[int, CarColor]] = []
        self._finish_line = FinishLine()
        self._last_detection_time: dict[int, float] = {}
        self._show_detection = True
        self.min_pixel_count = DEFAULT_MIN_PIXEL_COUNT

    def set_cars(self, cars: list[tuple[int, CarColor]]):
        self._car_entries = [(cid, c) for cid, c in cars if c.active]
        self._last_detection_time.clear()

    def set_finish_line(self, fl: FinishLine):
        self._finish_line = fl
        self._last_detection_time.clear()

    def run(self):
        cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.device_index)
        if not cap.isOpened():
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        # Optimize for speed: lower exposure = less motion blur
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)

        self._running = True
        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue

            display = frame.copy()
            self._detect(frame, display)
            self._draw_overlay(display)

            h, w, ch = display.shape
            img = QImage(display.data, w, h, ch * w, QImage.Format.Format_BGR888)
            self.frame_ready.emit(img.copy())

        cap.release()

    def stop(self):
        self._running = False
        self.wait(2000)

    def _detect(self, frame: np.ndarray, display: np.ndarray):
        if not self._finish_line.defined or not self._car_entries:
            return

        h, w = frame.shape[:2]
        now = time.monotonic()

        # Detection band (the zone that triggers crossings)
        bx1, by1, bx2, by2 = self._finish_line.get_detection_band(h, w)
        band = frame[by1:by2, bx1:bx2]
        if band.size == 0:
            return
        hsv_band = cv2.cvtColor(band, cv2.COLOR_BGR2HSV)

        for car_id, car in self._car_entries:
            # Color mask on the detection band
            mask = cv2.inRange(hsv_band, car.hsv_lower, car.hsv_upper)
            # Aggressive dilate to merge motion-blurred fragments
            mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)

            pixel_count = cv2.countNonZero(mask)

            # Draw overlay: show detected pixels
            if self._show_detection and pixel_count > 0:
                color_mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                band_display = display[by1:by2, bx1:bx2]
                # Tint detected pixels with car color
                tint = np.zeros_like(band_display)
                tint[:] = car.display_color
                blended = cv2.addWeighted(band_display, 0.7, tint, 0.3, 0)
                band_display[mask > 0] = blended[mask > 0]

                # Show pixel count
                cv2.putText(display, f"{car.name}:{pixel_count}px",
                            (bx1 + 4, by1 + 14),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, car.display_color, 1)

            # Trigger if enough color pixels in the band
            if pixel_count >= self.min_pixel_count:
                last = self._last_detection_time.get(car_id, 0)
                if (now - last) >= CROSSING_COOLDOWN_S:
                    self._last_detection_time[car_id] = now
                    self.crossing_detected.emit(car_id)

    def _draw_overlay(self, display: np.ndarray):
        if self._finish_line.defined:
            p1 = tuple(self._finish_line.p1.astype(int))
            p2 = tuple(self._finish_line.p2.astype(int))
            cv2.line(display, p1, p2, (0, 0, 255), 2)

            h, w = display.shape[:2]

            # Draw detection band border
            bx1, by1, bx2, by2 = self._finish_line.get_detection_band(h, w)
            cv2.rectangle(display, (bx1, by1), (bx2, by2), (0, 180, 0), 1)

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QImage, QPixmap, QMouseEvent


class VideoWidget(QLabel):
    finish_line_point = Signal(int, int)  # x, y
    color_sample_point = Signal(int, int)  # x, y

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #1a1a1a;")
        self.setText("Sin señal de cámara")
        self.setStyleSheet("background-color: #1a1a1a; color: #666; font-size: 14px;")

        self._mode = "normal"  # "normal", "finish_line", "color_sample"
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._offset_x = 0
        self._offset_y = 0
        self._frame_w = 640
        self._frame_h = 480

    def set_mode(self, mode: str):
        self._mode = mode
        if mode == "finish_line":
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif mode == "color_sample":
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def update_frame(self, image: QImage):
        self._frame_w = image.width()
        self._frame_h = image.height()
        pixmap = QPixmap.fromImage(image)
        scaled = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)

        self._scale_x = self._frame_w / scaled.width() if scaled.width() > 0 else 1
        self._scale_y = self._frame_h / scaled.height() if scaled.height() > 0 else 1
        self._offset_x = (self.width() - scaled.width()) // 2
        self._offset_y = (self.height() - scaled.height()) // 2

        self.setPixmap(scaled)

    def mousePressEvent(self, event: QMouseEvent):
        if self._mode == "normal":
            return

        local_x = event.position().x() - self._offset_x
        local_y = event.position().y() - self._offset_y
        frame_x = int(local_x * self._scale_x)
        frame_y = int(local_y * self._scale_y)

        frame_x = max(0, min(frame_x, self._frame_w - 1))
        frame_y = max(0, min(frame_y, self._frame_h - 1))

        if self._mode == "finish_line":
            self.finish_line_point.emit(frame_x, frame_y)
        elif self._mode == "color_sample":
            self.color_sample_point.emit(frame_x, frame_y)
            self.set_mode("normal")

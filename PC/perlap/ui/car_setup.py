from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QComboBox, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
import numpy as np


class CarSetupDialog(QDialog):
    car_registered = Signal(int, str, np.ndarray, np.ndarray, tuple)

    def __init__(self, max_cars: int = 6, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Auto")
        self.setMinimumWidth(300)
        self.setStyleSheet("background-color: #2a2a2a; color: white;")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Slot:"))
        self._slot_combo = QComboBox()
        for i in range(max_cars):
            self._slot_combo.addItem(f"Slot {i}", i)
        layout.addWidget(self._slot_combo)

        layout.addWidget(QLabel("Nombre del auto:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Ej: ROJO, P1, FERRARI...")
        self._name_edit.setMaxLength(12)
        layout.addWidget(self._name_edit)

        layout.addWidget(QLabel("Color (clic en el video para muestrear):"))
        self._color_preview = QFrame()
        self._color_preview.setFixedHeight(30)
        self._color_preview.setStyleSheet("background-color: #555; border: 1px solid #888;")
        layout.addWidget(self._color_preview)

        self._sample_btn = QPushButton("Muestrear Color del Video")
        self._sample_btn.setStyleSheet(
            "background-color: #444; padding: 8px; border: 1px solid #666;"
        )
        layout.addWidget(self._sample_btn)

        btn_layout = QHBoxLayout()
        self._ok_btn = QPushButton("Registrar")
        self._ok_btn.setStyleSheet(
            "background-color: #2d5a2d; padding: 8px; border: 1px solid #4a4a4a;"
        )
        self._ok_btn.setEnabled(False)
        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setStyleSheet(
            "background-color: #5a2d2d; padding: 8px; border: 1px solid #4a4a4a;"
        )
        btn_layout.addWidget(self._ok_btn)
        btn_layout.addWidget(self._cancel_btn)
        layout.addLayout(btn_layout)

        self._hsv_lower = None
        self._hsv_upper = None
        self._display_color = (255, 255, 255)

        self._ok_btn.clicked.connect(self._on_ok)
        self._cancel_btn.clicked.connect(self.reject)
        self._sample_btn.clicked.connect(self._on_sample)

    @property
    def wants_sample(self) -> bool:
        return self._sample_btn is not None

    def _on_sample(self):
        self._sample_btn.setText("Haz clic en el auto en el video...")
        self._sample_btn.setEnabled(False)

    def set_sampled_color(self, hsv_lower: np.ndarray, hsv_upper: np.ndarray,
                          display_color: tuple):
        self._hsv_lower = hsv_lower
        self._hsv_upper = hsv_upper
        self._display_color = display_color

        r, g, b = display_color[2], display_color[1], display_color[0]  # BGR to RGB
        self._color_preview.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border: 1px solid #888;"
        )
        self._ok_btn.setEnabled(True)
        self._sample_btn.setText("Muestrear Color del Video")
        self._sample_btn.setEnabled(True)

    def _on_ok(self):
        name = self._name_edit.text().strip().upper()
        if not name:
            return
        slot = self._slot_combo.currentData()
        if self._hsv_lower is None:
            return
        self.car_registered.emit(
            slot, name, self._hsv_lower, self._hsv_upper, self._display_color
        )
        self.accept()

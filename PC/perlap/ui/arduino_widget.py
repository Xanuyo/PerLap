from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QSlider, QSpinBox, QComboBox,
                               QProgressBar, QFrame)
from PySide6.QtCore import Qt, Signal


class ArduinoCalibrationWidget(QWidget):
    """Live LDR calibration panel for laser alignment."""

    threshold_changed = Signal(int)
    laser_toggled = Signal(bool)
    recalibrate_requested = Signal()
    port_changed = Signal(str)
    refresh_ports_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._threshold = 400
        self._ldr_value = 0
        self._baseline = 0
        self._laser_on = True
        self._connected = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("CALIBRACION LASER")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #0af;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(10)

        # ── LDR value display ──
        ldr_frame = QFrame()
        ldr_frame.setStyleSheet(
            "QFrame { background: #2a2a2a; border: 1px solid #444; "
            "border-radius: 8px; padding: 16px; }"
        )
        ldr_layout = QVBoxLayout(ldr_frame)

        self._ldr_label = QLabel("LDR: -- / 1023")
        self._ldr_label.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        self._ldr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ldr_layout.addWidget(self._ldr_label)

        self._ldr_bar = QProgressBar()
        self._ldr_bar.setRange(0, 1023)
        self._ldr_bar.setValue(0)
        self._ldr_bar.setFixedHeight(30)
        self._ldr_bar.setTextVisible(False)
        self._ldr_bar.setStyleSheet(
            "QProgressBar { background: #333; border: 1px solid #555; border-radius: 4px; }"
            "QProgressBar::chunk { background: #0a0; border-radius: 3px; }"
        )
        ldr_layout.addWidget(self._ldr_bar)

        self._threshold_marker_label = QLabel("Umbral: --")
        self._threshold_marker_label.setStyleSheet("font-size: 12px; color: #888;")
        self._threshold_marker_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ldr_layout.addWidget(self._threshold_marker_label)

        layout.addWidget(ldr_frame)

        # ── Status indicator ──
        self._status_label = QLabel("Estado: SIN CONEXION")
        self._status_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #888; padding: 8px;"
        )
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        # ── Threshold control ──
        thresh_frame = QFrame()
        thresh_frame.setStyleSheet(
            "QFrame { background: #2a2a2a; border: 1px solid #444; "
            "border-radius: 8px; padding: 12px; }"
        )
        thresh_layout = QVBoxLayout(thresh_frame)

        thresh_label = QLabel("Umbral de deteccion:")
        thresh_label.setStyleSheet("font-size: 14px; color: #ccc;")
        thresh_layout.addWidget(thresh_label)

        slider_row = QHBoxLayout()
        self._thresh_slider = QSlider(Qt.Orientation.Horizontal)
        self._thresh_slider.setRange(10, 1023)
        self._thresh_slider.setValue(400)
        self._thresh_slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #555; height: 8px; border-radius: 4px; }"
            "QSlider::handle:horizontal { background: #0af; width: 18px; "
            "margin: -5px 0; border-radius: 9px; }"
        )
        self._thresh_slider.valueChanged.connect(self._on_thresh_slider)
        slider_row.addWidget(self._thresh_slider)

        self._thresh_spin = QSpinBox()
        self._thresh_spin.setRange(10, 1023)
        self._thresh_spin.setValue(400)
        self._thresh_spin.setStyleSheet(
            "QSpinBox { background: #444; color: white; padding: 4px; "
            "border: 1px solid #666; min-width: 60px; font-size: 14px; }"
        )
        self._thresh_spin.valueChanged.connect(self._on_thresh_spin)
        slider_row.addWidget(self._thresh_spin)

        thresh_layout.addLayout(slider_row)
        layout.addWidget(thresh_frame)

        # ── Buttons row ──
        btn_row = QHBoxLayout()

        self._laser_btn = QPushButton("Laser: ON")
        self._laser_btn.setStyleSheet(
            "QPushButton { background: #2d5a2d; color: white; padding: 10px 20px; "
            "border: 1px solid #4a4a4a; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background: #3d6a3d; }"
        )
        self._laser_btn.clicked.connect(self._on_laser_toggle)
        btn_row.addWidget(self._laser_btn)

        self._recal_btn = QPushButton("Recalibrar")
        self._recal_btn.setStyleSheet(
            "QPushButton { background: #444; color: white; padding: 10px 20px; "
            "border: 1px solid #666; font-size: 14px; }"
            "QPushButton:hover { background: #555; }"
        )
        self._recal_btn.clicked.connect(self.recalibrate_requested.emit)
        btn_row.addWidget(self._recal_btn)

        layout.addLayout(btn_row)

        # ── Port selector ──
        port_frame = QFrame()
        port_frame.setStyleSheet(
            "QFrame { background: #2a2a2a; border: 1px solid #444; "
            "border-radius: 8px; padding: 12px; }"
        )
        port_layout = QHBoxLayout(port_frame)

        port_layout.addWidget(QLabel("Puerto:"))

        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(200)
        self._port_combo.setStyleSheet(
            "QComboBox { background: #444; color: white; padding: 6px; }"
        )
        self._port_combo.currentTextChanged.connect(self._on_port_changed)
        port_layout.addWidget(self._port_combo)

        self._refresh_btn = QPushButton("Buscar")
        self._refresh_btn.setStyleSheet(
            "QPushButton { background: #444; color: white; padding: 6px 12px; "
            "border: 1px solid #666; }"
            "QPushButton:hover { background: #555; }"
        )
        self._refresh_btn.clicked.connect(self.refresh_ports_requested.emit)
        port_layout.addWidget(self._refresh_btn)

        self._conn_label = QLabel("Desconectado")
        self._conn_label.setStyleSheet("color: #f44; font-weight: bold;")
        port_layout.addWidget(self._conn_label)

        layout.addWidget(port_frame)

        layout.addStretch()

    # ── Public slots ──

    def update_ldr(self, value: int):
        self._ldr_value = value
        self._ldr_label.setText(f"LDR: {value} / 1023")
        self._ldr_bar.setValue(value)

        if value >= self._threshold:
            self._ldr_bar.setStyleSheet(
                "QProgressBar { background: #333; border: 1px solid #555; border-radius: 4px; }"
                "QProgressBar::chunk { background: #0a0; border-radius: 3px; }"
            )
            self._status_label.setText("Estado: LASER ALINEADO")
            self._status_label.setStyleSheet(
                "font-size: 20px; font-weight: bold; color: #0a0; padding: 8px;"
            )
        else:
            self._ldr_bar.setStyleSheet(
                "QProgressBar { background: #333; border: 1px solid #555; border-radius: 4px; }"
                "QProgressBar::chunk { background: #f44; border-radius: 3px; }"
            )
            self._status_label.setText("Estado: HAZ CORTADO")
            self._status_label.setStyleSheet(
                "font-size: 20px; font-weight: bold; color: #f44; padding: 8px;"
            )

    def set_confirmed_threshold(self, value: int):
        self._threshold = value
        self._thresh_slider.blockSignals(True)
        self._thresh_spin.blockSignals(True)
        self._thresh_slider.setValue(value)
        self._thresh_spin.setValue(value)
        self._thresh_slider.blockSignals(False)
        self._thresh_spin.blockSignals(False)
        self._threshold_marker_label.setText(f"Umbral: {value}")

    def set_baseline(self, baseline: int, threshold: int):
        self._baseline = baseline
        self._threshold = threshold
        self.set_confirmed_threshold(threshold)

    def set_connection_state(self, connected: bool):
        self._connected = connected
        if connected:
            self._conn_label.setText("Conectado")
            self._conn_label.setStyleSheet("color: #0a0; font-weight: bold;")
        else:
            self._conn_label.setText("Desconectado")
            self._conn_label.setStyleSheet("color: #f44; font-weight: bold;")
            self._status_label.setText("Estado: SIN CONEXION")
            self._status_label.setStyleSheet(
                "font-size: 20px; font-weight: bold; color: #888; padding: 8px;"
            )

    def update_ports(self, ports: list[tuple[str, str]], current_port: str = ""):
        self._port_combo.blockSignals(True)
        self._port_combo.clear()
        for device, desc in ports:
            self._port_combo.addItem(f"{device} - {desc}", device)
        if current_port:
            for i in range(self._port_combo.count()):
                if self._port_combo.itemData(i) == current_port:
                    self._port_combo.setCurrentIndex(i)
                    break
        self._port_combo.blockSignals(False)

    @property
    def threshold(self) -> int:
        return self._threshold

    @property
    def selected_port(self) -> str:
        return self._port_combo.currentData() or ""

    # ── Internal slots ──

    def _on_thresh_slider(self, value: int):
        self._thresh_spin.blockSignals(True)
        self._thresh_spin.setValue(value)
        self._thresh_spin.blockSignals(False)
        self._threshold = value
        self._threshold_marker_label.setText(f"Umbral: {value}")
        self.threshold_changed.emit(value)

    def _on_thresh_spin(self, value: int):
        self._thresh_slider.blockSignals(True)
        self._thresh_slider.setValue(value)
        self._thresh_slider.blockSignals(False)
        self._threshold = value
        self._threshold_marker_label.setText(f"Umbral: {value}")
        self.threshold_changed.emit(value)

    def _on_laser_toggle(self):
        self._laser_on = not self._laser_on
        if self._laser_on:
            self._laser_btn.setText("Laser: ON")
            self._laser_btn.setStyleSheet(
                "QPushButton { background: #2d5a2d; color: white; padding: 10px 20px; "
                "border: 1px solid #4a4a4a; font-size: 14px; font-weight: bold; }"
                "QPushButton:hover { background: #3d6a3d; }"
            )
        else:
            self._laser_btn.setText("Laser: OFF")
            self._laser_btn.setStyleSheet(
                "QPushButton { background: #5a2d2d; color: white; padding: 10px 20px; "
                "border: 1px solid #4a4a4a; font-size: 14px; font-weight: bold; }"
                "QPushButton:hover { background: #6a3d3d; }"
            )
        self.laser_toggled.emit(self._laser_on)

    def _on_port_changed(self, text: str):
        port = self._port_combo.currentData()
        if port:
            self.port_changed.emit(port)

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QFrame)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from .standings import format_time


class TimeTrialWidget(QWidget):
    trial_started = Signal()
    trial_reset = Signal()
    name_submitted = Signal(str)  # player name

    def __init__(self, total_laps: int = 5, parent=None):
        super().__init__(parent)
        self.total_laps = total_laps
        self._running = False
        self._finished = False
        self._elapsed_timer = QTimer()
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._elapsed_ms = 0

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QLabel("CONTRARRELOJ")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(f"{self.total_laps} vueltas - Mejor tiempo gana")
        subtitle.setStyleSheet("font-size: 12px; color: #aaa;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color: #444;")
        layout.addWidget(sep1)

        # Lap counter
        self._lap_label = QLabel("- / %d" % self.total_laps)
        self._lap_label.setFont(QFont("Consolas", 32, QFont.Weight.Bold))
        self._lap_label.setStyleSheet("color: white;")
        self._lap_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lap_label)

        lbl = QLabel("VUELTA")
        lbl.setStyleSheet("font-size: 11px; color: #888;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        # Total time
        self._total_label = QLabel("0.000s")
        self._total_label.setFont(QFont("Consolas", 26, QFont.Weight.Bold))
        self._total_label.setStyleSheet("color: #0f0;")
        self._total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._total_label)

        lbl2 = QLabel("TIEMPO TOTAL")
        lbl2.setStyleSheet("font-size: 11px; color: #888;")
        lbl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl2)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #444;")
        layout.addWidget(sep2)

        # Individual lap times
        self._laps_container = QVBoxLayout()
        self._lap_rows: list[QLabel] = []
        for i in range(self.total_laps):
            row = QLabel(f"  Vuelta {i+1}:  ---")
            row.setStyleSheet("font-size: 14px; color: #888; font-family: Consolas;")
            self._laps_container.addWidget(row)
            self._lap_rows.append(row)
        layout.addLayout(self._laps_container)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet("color: #444;")
        layout.addWidget(sep3)

        # Last lap flash
        self._last_lap_label = QLabel("")
        self._last_lap_label.setFont(QFont("Consolas", 16))
        self._last_lap_label.setStyleSheet("color: #0ff;")
        self._last_lap_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._last_lap_label)

        # Status / instructions
        self._status_label = QLabel("Cruza la meta para comenzar")
        self._status_label.setStyleSheet("font-size: 13px; color: #aaa;")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        # Name input (hidden until finish)
        self._name_frame = QWidget()
        self._name_frame.setVisible(False)
        name_layout = QVBoxLayout(self._name_frame)
        name_layout.setContentsMargins(4, 10, 4, 4)
        name_layout.setSpacing(8)

        name_title = QLabel("Tu nombre para el ranking:")
        name_title.setStyleSheet("font-size: 14px; color: #ff0;")
        name_layout.addWidget(name_title)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Nombre...")
        self._name_input.setMaxLength(20)
        self._name_input.setMinimumHeight(40)
        self._name_input.setStyleSheet(
            "QLineEdit { background: #333; color: white; padding: 8px; "
            "border: 2px solid #666; font-size: 18px; font-family: Consolas; }"
        )
        self._name_input.returnPressed.connect(self._on_submit)
        name_layout.addWidget(self._name_input)

        self._submit_btn = QPushButton("GUARDAR EN RANKING")
        self._submit_btn.setMinimumHeight(40)
        self._submit_btn.setStyleSheet(
            "QPushButton { background: #2d7a2d; color: white; padding: 8px; "
            "border: none; font-size: 16px; font-weight: bold; }"
            "QPushButton:hover { background: #3a9a3a; }"
        )
        self._submit_btn.clicked.connect(self._on_submit)
        name_layout.addWidget(self._submit_btn)

        layout.addWidget(self._name_frame)

        # Reset button
        self._reset_btn = QPushButton("Nueva Contrarreloj")
        self._reset_btn.setStyleSheet(
            "background: #444; color: white; padding: 8px; "
            "border: 1px solid #666; font-size: 13px; margin-top: 8px;"
        )
        self._reset_btn.clicked.connect(self._on_reset)
        layout.addWidget(self._reset_btn)

        layout.addStretch()

    def on_start(self):
        self._running = True
        self._finished = False
        self._elapsed_ms = 0
        self._elapsed_timer.start(50)
        self._lap_label.setText("0 / %d" % self.total_laps)
        self._status_label.setText("En pista - sigue corriendo!")
        self._last_lap_label.setText("")
        self._name_frame.setVisible(False)

    def on_lap(self, lap_number: int, lap_time_ms: int, total_ms: int, best_lap_ms: int):
        self._lap_label.setText(f"{lap_number} / {self.total_laps}")
        self._total_label.setText(format_time(total_ms))
        self._elapsed_ms = total_ms

        idx = lap_number - 1
        if 0 <= idx < len(self._lap_rows):
            time_str = format_time(lap_time_ms)
            self._lap_rows[idx].setStyleSheet(
                "font-size: 14px; color: white; font-family: Consolas;"
            )
            is_best = (lap_time_ms == best_lap_ms)
            if is_best:
                self._lap_rows[idx].setText(f"  Vuelta {idx+1}:  {time_str}  *MEJOR*")
                self._lap_rows[idx].setStyleSheet(
                    "font-size: 14px; color: #f0f; font-family: Consolas;"
                )
            else:
                self._lap_rows[idx].setText(f"  Vuelta {idx+1}:  {time_str}")

        self._last_lap_label.setText(f"V{lap_number}: {format_time(lap_time_ms)}")

    def on_finish(self, total_ms: int):
        self._running = False
        self._finished = True
        self._elapsed_timer.stop()
        self._total_label.setText(format_time(total_ms))
        self._total_label.setStyleSheet("color: #ff0; font-size: 28px;")
        self._lap_label.setText(f"{self.total_laps} / {self.total_laps}")
        self._status_label.setText("TERMINADO!")
        self._status_label.setStyleSheet("font-size: 16px; color: #0f0; font-weight: bold;")
        self._name_frame.setVisible(True)
        self._name_input.setFocus()

    def _on_submit(self):
        name = self._name_input.text().strip()
        if not name:
            self._name_input.setStyleSheet(
                "background: #333; color: white; padding: 8px; "
                "border: 2px solid #f00; font-size: 14px;"
            )
            return
        self._name_frame.setVisible(False)
        self._status_label.setText(f"Guardado: {name}")
        self.name_submitted.emit(name)

    def _on_reset(self):
        self._running = False
        self._finished = False
        self._elapsed_timer.stop()
        self._elapsed_ms = 0
        self._lap_label.setText("- / %d" % self.total_laps)
        self._total_label.setText("0.000s")
        self._total_label.setStyleSheet("color: #0f0;")
        self._last_lap_label.setText("")
        self._status_label.setText("Cruza la meta para comenzar")
        self._status_label.setStyleSheet("font-size: 13px; color: #aaa;")
        self._name_frame.setVisible(False)
        self._name_input.clear()
        for i, row in enumerate(self._lap_rows):
            row.setText(f"  Vuelta {i+1}:  ---")
            row.setStyleSheet("font-size: 14px; color: #888; font-family: Consolas;")
        self.trial_reset.emit()

    def _update_elapsed(self):
        if self._running:
            self._elapsed_ms += 50
            self._total_label.setText(format_time(self._elapsed_ms))

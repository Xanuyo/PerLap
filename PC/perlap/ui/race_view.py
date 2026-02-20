from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget,
                               QTableWidgetItem, QHeaderView, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush

from ..models.events import LapEvent, EventType
from .standings import format_time


class RaceViewWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("TIEMPOS POR VUELTA")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self._lap_table = QTableWidget()
        self._lap_table.setColumnCount(4)
        self._lap_table.setHorizontalHeaderLabels(["Auto", "Vuelta", "Tiempo", "Gap"])
        self._lap_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._lap_table.verticalHeader().setVisible(False)
        self._lap_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._lap_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._lap_table.setStyleSheet("""
            QTableWidget { background-color: #2a2a2a; color: white; gridline-color: #444; }
            QHeaderView::section { background-color: #333; color: #ccc; padding: 4px; }
        """)
        layout.addWidget(self._lap_table)

        self._fastest_label = QLabel("")
        self._fastest_label.setStyleSheet("font-size: 12px; color: #f0f; padding: 4px;")
        layout.addWidget(self._fastest_label)

        self._events: list[LapEvent] = []
        self._fastest_lap_ms = 999999
        self._fastest_lap_car = ""

    def add_event(self, event: LapEvent):
        if event.event != EventType.LAP:
            return
        self._events.append(event)

        if event.lap_time_ms < self._fastest_lap_ms:
            self._fastest_lap_ms = event.lap_time_ms
            self._fastest_lap_car = event.car_name
            self._fastest_label.setText(
                f"Vuelta rápida: {event.car_name} - {format_time(event.lap_time_ms)}"
            )

        self._refresh_table()

    def _refresh_table(self):
        self._lap_table.setRowCount(len(self._events))
        for row, ev in enumerate(reversed(self._events)):
            items = [
                ev.car_name,
                str(ev.lap_number),
                format_time(ev.lap_time_ms),
                format_time(ev.lap_time_ms - self._fastest_lap_ms)
                if ev.lap_time_ms > self._fastest_lap_ms else "RÁPIDA",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 3 and text == "RÁPIDA":
                    item.setForeground(QBrush(QColor(255, 0, 255)))
                self._lap_table.setItem(row, col, item)

    def clear(self):
        self._events.clear()
        self._fastest_lap_ms = 999999
        self._fastest_lap_car = ""
        self._fastest_label.setText("")
        self._lap_table.setRowCount(0)

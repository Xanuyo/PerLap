from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget,
                               QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush


def format_time(ms: int) -> str:
    if ms <= 0:
        return "-"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.3f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:06.3f}"


class StandingsWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("CLASIFICACIÓN")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["Pos", "Auto", "Vtas", "Mejor", "Última"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 35)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setStyleSheet("""
            QTableWidget { background-color: #2a2a2a; color: white; gridline-color: #444; }
            QHeaderView::section { background-color: #333; color: #ccc; padding: 4px; }
        """)
        layout.addWidget(self._table)

        self._last_event_label = QLabel("")
        self._last_event_label.setStyleSheet(
            "font-size: 13px; color: #0f0; padding: 4px;"
        )
        self._last_event_label.setWordWrap(True)
        layout.addWidget(self._last_event_label)

    def update_standings(self, standings: list[dict]):
        self._table.setRowCount(len(standings))
        for row, s in enumerate(standings):
            color = QColor(*s["color"][::-1]) if s.get("color") else QColor(255, 255, 255)
            items = [
                str(row + 1),
                s["name"],
                str(s["laps"]),
                format_time(s["best_ms"]),
                format_time(s["last_ms"]),
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 1:
                    item.setForeground(QBrush(color))
                self._table.setItem(row, col, item)

    def show_event(self, text: str):
        self._last_event_label.setText(text)

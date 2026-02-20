from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont

from .standings import format_time
from ..models.time_trial import TimeTrial


class RankingWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("RANKING CONTRARRELOJ")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["#", "Jugador", "Total", "Mejor Vta", "Fecha"]
        )
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 35)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a; color: white;
                gridline-color: #444; font-size: 13px;
            }
            QHeaderView::section {
                background-color: #333; color: #ccc; padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #3a3a1a;
            }
        """)
        layout.addWidget(self._table)

        # Detail label for selected row
        self._detail_label = QLabel("")
        self._detail_label.setStyleSheet("font-size: 12px; color: #aaa; padding: 4px;")
        self._detail_label.setWordWrap(True)
        layout.addWidget(self._detail_label)

        # Buttons row
        btn_row = QHBoxLayout()

        self._btn_delete = QPushButton("Borrar seleccion")
        self._btn_delete.setStyleSheet(
            "background: #5a3a2d; color: white; padding: 6px 10px; "
            "border: 1px solid #666; font-size: 12px;"
        )
        self._btn_delete.clicked.connect(self._on_delete_selected)
        btn_row.addWidget(self._btn_delete)

        self._btn_clear = QPushButton("Borrar todo")
        self._btn_clear.setStyleSheet(
            "background: #5a2d2d; color: white; padding: 6px 10px; "
            "border: 1px solid #666; font-size: 12px;"
        )
        self._btn_clear.clicked.connect(self._on_clear_all)
        btn_row.addWidget(self._btn_clear)

        layout.addLayout(btn_row)

        self._ranking_data: list[dict] = []
        self._table.currentCellChanged.connect(self._on_row_selected)

        self.refresh()

    def refresh(self):
        self._ranking_data = TimeTrial.load_ranking()
        self._table.setRowCount(len(self._ranking_data))

        gold = QColor(255, 215, 0)
        silver = QColor(192, 192, 192)
        bronze = QColor(205, 127, 50)

        for row, entry in enumerate(self._ranking_data):
            date_str = entry.get("date", "")[:10]
            items = [
                str(row + 1),
                entry.get("player", "???"),
                format_time(entry.get("total_ms", 0)),
                format_time(entry.get("best_lap_ms", 0)),
                date_str,
            ]

            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if row == 0:
                    item.setForeground(QBrush(gold))
                    if col == 0:
                        item.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
                elif row == 1:
                    item.setForeground(QBrush(silver))
                elif row == 2:
                    item.setForeground(QBrush(bronze))

                self._table.setItem(row, col, item)

        self._detail_label.setText(
            f"{len(self._ranking_data)} jugadores en el ranking"
        )

    def highlight_player(self, player_name: str):
        for row, entry in enumerate(self._ranking_data):
            if entry.get("player") == player_name:
                self._table.selectRow(row)
                self._table.scrollTo(self._table.model().index(row, 0))
                break

    def _on_row_selected(self, row, col, prev_row, prev_col):
        if row < 0 or row >= len(self._ranking_data):
            self._detail_label.setText("")
            return
        entry = self._ranking_data[row]
        laps = entry.get("lap_times_ms", [])
        lap_strs = [f"V{i+1}: {format_time(t)}" for i, t in enumerate(laps)]
        self._detail_label.setText(
            f"{entry.get('player', '???')} - {' | '.join(lap_strs)}"
        )

    def _on_delete_selected(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._ranking_data):
            return
        entry = self._ranking_data[row]
        name = entry.get("player", "???")
        total = format_time(entry.get("total_ms", 0))
        reply = QMessageBox.question(
            self, "Borrar marca",
            f"Borrar a {name} ({total}) del ranking?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._ranking_data.pop(row)
            TimeTrial.save_ranking(self._ranking_data)
            self.refresh()

    def _on_clear_all(self):
        if not self._ranking_data:
            return
        reply = QMessageBox.question(
            self, "Borrar ranking",
            f"Borrar las {len(self._ranking_data)} marcas del ranking?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            TimeTrial.save_ranking([])
            self.refresh()

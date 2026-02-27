import json
import os

from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QPushButton, QToolBar, QStatusBar, QMessageBox,
                               QSplitter, QTabWidget, QComboBox, QLabel,
                               QStackedWidget, QSlider, QSpinBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QAction
import numpy as np
import cv2

from ..models.race import RaceManager, MAX_CARS
from ..models.race_log import RaceLog
from ..models.time_trial import TimeTrial
from ..models.events import LapEvent, EventType
from ..detection.camera import CameraSource, DEFAULT_MIN_PIXEL_COUNT
from ..detection.finish_line import FinishLine
from ..detection.color_id import ColorCalibrator, SENSITIVITY_PRESETS, DEFAULT_SENSITIVITY
from ..detection.arduino import ArduinoSource
from .video_widget import VideoWidget
from .standings import StandingsWidget, format_time
from .car_setup import CarSetupDialog
from .race_view import RaceViewWidget
from .time_trial_widget import TimeTrialWidget
from .ranking_widget import RankingWidget
from .arduino_widget import ArduinoCalibrationWidget

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                           "config.json")

MODE_RACE = 0
MODE_TIME_TRIAL = 1

SOURCE_CAMERA = "CAMERA"
SOURCE_ARDUINO = "ARDUINO"


class MainWindow(QMainWindow):

    def __init__(self, race_manager: RaceManager, camera_source: CameraSource,
                 arduino_source: ArduinoSource | None = None):
        super().__init__()
        self.setWindowTitle("PerLap - Cronometro de Vueltas RC")
        self.setMinimumSize(960, 600)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")

        self._race = race_manager
        self._camera = camera_source
        self._arduino = arduino_source or ArduinoSource()
        self._race_log = RaceLog()
        self._time_trial = TimeTrial()
        self._finish_line = FinishLine()
        self._fl_points: list[tuple[int, int]] = []
        self._last_frame_bgr: np.ndarray | None = None
        self._car_setup_dialog: CarSetupDialog | None = None
        self._fps_count = 0
        self._racing = False
        self._mode = MODE_RACE
        self._detection_source = SOURCE_CAMERA

        self._setup_ui()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()
        self._load_config()

        self._fps_timer = QTimer()
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start(1000)

    # -----------------------------------------------------------
    # UI Setup
    # -----------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: stacked (video / arduino calibration)
        self._left_stack = QStackedWidget()

        self._video = VideoWidget()
        self._left_stack.addWidget(self._video)  # index 0

        self._arduino_widget = ArduinoCalibrationWidget()
        self._left_stack.addWidget(self._arduino_widget)  # index 1

        splitter.addWidget(self._left_stack)

        # Right panel: stacked widget that switches with mode
        self._right_stack = QStackedWidget()

        # --- Page 0: Race mode tabs ---
        self._race_tabs = QTabWidget()
        self._race_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #333; color: #ccc; padding: 6px 12px; }
            QTabBar::tab:selected { background: #444; color: white; }
        """)

        self._standings = StandingsWidget()
        self._race_tabs.addTab(self._standings, "Clasificacion")

        self._race_view = RaceViewWidget()
        self._race_tabs.addTab(self._race_view, "Tiempos")

        self._right_stack.addWidget(self._race_tabs)

        # --- Page 1: Time trial tabs ---
        self._tt_tabs = QTabWidget()
        self._tt_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #333; color: #ccc; padding: 6px 12px; }
            QTabBar::tab:selected { background: #444; color: white; }
        """)

        self._tt_widget = TimeTrialWidget(total_laps=5)
        self._tt_tabs.addTab(self._tt_widget, "Contrarreloj")

        self._ranking_widget = RankingWidget()
        self._tt_tabs.addTab(self._ranking_widget, "Ranking")

        self._right_stack.addWidget(self._tt_tabs)

        splitter.addWidget(self._right_stack)
        splitter.setSizes([680, 280])

        layout.addWidget(splitter)

    def _setup_toolbar(self):
        toolbar = QToolBar("Controles")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(
            "QToolBar { background: #2a2a2a; spacing: 4px; padding: 2px; }"
            "QPushButton { background: #444; color: white; padding: 6px 12px; "
            "border: 1px solid #666; }"
            "QPushButton:hover { background: #555; }"
            "QComboBox { background: #444; color: white; padding: 4px; }"
        )
        self.addToolBar(toolbar)

        # Source selector
        toolbar.addWidget(QLabel(" Fuente: "))
        self._source_combo = QComboBox()
        self._source_combo.addItem("Camara USB", SOURCE_CAMERA)
        self._source_combo.addItem("Arduino Laser", SOURCE_ARDUINO)
        self._source_combo.currentIndexChanged.connect(self._on_source_changed)
        toolbar.addWidget(self._source_combo)

        toolbar.addSeparator()

        # Mode selector
        toolbar.addWidget(QLabel(" Modo: "))
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Carrera", MODE_RACE)
        self._mode_combo.addItem("Contrarreloj", MODE_TIME_TRIAL)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        toolbar.addWidget(self._mode_combo)

        toolbar.addSeparator()

        btn_reg = QPushButton("Registrar Auto")
        btn_reg.clicked.connect(self._on_register_car)
        self._btn_register = btn_reg
        toolbar.addWidget(btn_reg)

        btn_line = QPushButton("Definir Meta")
        btn_line.clicked.connect(self._on_define_finish_line)
        self._btn_line = btn_line
        toolbar.addWidget(btn_line)

        toolbar.addSeparator()

        # Race controls (visible in race mode)
        self._btn_race = QPushButton("Iniciar Carrera")
        self._btn_race.setStyleSheet(
            "background-color: #2d5a2d; padding: 6px 12px; border: 1px solid #4a4a4a;"
        )
        self._btn_race.clicked.connect(self._on_toggle_race)
        toolbar.addWidget(self._btn_race)

        self._btn_reset = QPushButton("Reiniciar")
        self._btn_reset.clicked.connect(self._on_reset)
        toolbar.addWidget(self._btn_reset)

        toolbar.addSeparator()

        # --- Camera-specific controls ---
        self._cam_label = QLabel(" Camara: ")
        toolbar.addWidget(self._cam_label)
        self._cam_combo = QComboBox()
        for i in range(5):
            self._cam_combo.addItem(f"Dispositivo {i}", i)
        self._cam_combo.currentIndexChanged.connect(self._on_camera_changed)
        toolbar.addWidget(self._cam_combo)

        toolbar.addSeparator()

        self._sens_label = QLabel(" Sensibilidad: ")
        toolbar.addWidget(self._sens_label)
        self._sens_combo = QComboBox()
        for name in SENSITIVITY_PRESETS:
            self._sens_combo.addItem(name)
        self._sens_combo.setCurrentText(DEFAULT_SENSITIVITY)
        self._sens_combo.currentTextChanged.connect(self._on_sensitivity_changed)
        toolbar.addWidget(self._sens_combo)

        toolbar.addSeparator()

        self._px_label = QLabel(" Min px: ")
        toolbar.addWidget(self._px_label)
        self._px_slider = QSlider(Qt.Orientation.Horizontal)
        self._px_slider.setRange(10, 500)
        self._px_slider.setValue(DEFAULT_MIN_PIXEL_COUNT)
        self._px_slider.setFixedWidth(120)
        self._px_slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #555; height: 6px; }"
            "QSlider::handle:horizontal { background: #0af; width: 14px; "
            "margin: -4px 0; border-radius: 7px; }"
        )
        self._px_slider.valueChanged.connect(self._on_min_px_changed)
        toolbar.addWidget(self._px_slider)

        self._px_spin = QSpinBox()
        self._px_spin.setRange(10, 500)
        self._px_spin.setValue(DEFAULT_MIN_PIXEL_COUNT)
        self._px_spin.setStyleSheet(
            "QSpinBox { background: #444; color: white; padding: 2px 4px; "
            "border: 1px solid #666; min-width: 50px; }"
        )
        self._px_spin.valueChanged.connect(self._on_min_px_changed)
        toolbar.addWidget(self._px_spin)

        # Collect camera-only widgets for show/hide
        self._camera_controls = [
            self._cam_label, self._cam_combo,
            self._sens_label, self._sens_combo,
            self._px_label, self._px_slider, self._px_spin,
            self._btn_register, self._btn_line,
        ]

    def _setup_statusbar(self):
        self._status = QStatusBar()
        self._status.setStyleSheet("background: #2a2a2a; color: #aaa;")
        self.setStatusBar(self._status)
        self._fps_label = QLabel("FPS: --")
        self._source_label = QLabel("Fuente: Camara USB")
        self._cars_label = QLabel("Autos: 0/6")
        self._mode_label = QLabel("Modo: Carrera")
        self._status.addWidget(self._source_label)
        self._status.addWidget(self._fps_label)
        self._status.addWidget(self._mode_label)
        self._status.addPermanentWidget(self._cars_label)

    def _connect_signals(self):
        # Camera signals
        self._camera.frame_ready.connect(self._on_frame)
        self._camera.crossing_detected.connect(
            lambda car_id: self._on_crossing(car_id, "CAMERA")
        )
        self._video.finish_line_point.connect(self._on_fl_point)
        self._video.color_sample_point.connect(self._on_color_sample)
        self._tt_widget.name_submitted.connect(self._on_tt_name_submitted)
        self._tt_widget.trial_reset.connect(self._on_tt_reset)

        # Arduino signals
        self._arduino.crossing_detected.connect(
            lambda car_id: self._on_crossing(car_id, "ARDUINO")
        )
        self._arduino.ldr_value.connect(self._arduino_widget.update_ldr)
        self._arduino.connection_changed.connect(self._on_arduino_connection)
        self._arduino.threshold_changed.connect(
            self._arduino_widget.set_confirmed_threshold
        )
        self._arduino.ready.connect(self._arduino_widget.set_baseline)
        self._arduino.error_occurred.connect(
            lambda msg: self._status.showMessage(f"Arduino: {msg}", 5000)
        )

        # Arduino widget signals
        self._arduino_widget.threshold_changed.connect(self._arduino.set_threshold)
        self._arduino_widget.laser_toggled.connect(self._arduino.set_laser)
        self._arduino_widget.recalibrate_requested.connect(self._arduino.request_reset)
        self._arduino_widget.test_requested.connect(self._arduino.request_test)
        self._arduino_widget.port_changed.connect(self._on_arduino_port_changed)
        self._arduino_widget.refresh_ports_requested.connect(self._refresh_arduino_ports)

        self._arduino.test_result.connect(self._arduino_widget.show_test_result)

    # -----------------------------------------------------------
    # Detection source switching
    # -----------------------------------------------------------

    def _on_source_changed(self, index: int):
        source = self._source_combo.currentData()
        self._detection_source = source

        if source == SOURCE_ARDUINO:
            self._camera.stop()
            self._left_stack.setCurrentIndex(1)
            self._source_label.setText("Fuente: Arduino Laser")

            # Hide camera controls
            for w in self._camera_controls:
                w.setVisible(False)

            # Refresh ports and start Arduino
            self._refresh_arduino_ports()
            port = self._arduino_widget.selected_port
            if port:
                self._arduino.port = port
                self._arduino.start()
                self._arduino.set_streaming(True)
        else:
            # Stop Arduino
            if self._arduino.isRunning():
                self._arduino.set_streaming(False)
                self._arduino.stop()

            self._left_stack.setCurrentIndex(0)
            self._source_label.setText("Fuente: Camara USB")

            # Show camera controls
            for w in self._camera_controls:
                w.setVisible(True)

            self._camera.start()

        self._save_config()

    def _on_arduino_port_changed(self, port: str):
        was_running = self._arduino.isRunning()
        if was_running:
            self._arduino.set_streaming(False)
            self._arduino.stop()
        self._arduino.port = port
        if self._detection_source == SOURCE_ARDUINO and port:
            self._arduino.start()
            self._arduino.set_streaming(True)
        self._save_config()

    def _on_arduino_connection(self, connected: bool):
        self._arduino_widget.set_connection_state(connected)
        if connected:
            self._status.showMessage("Arduino conectado", 3000)
        else:
            self._status.showMessage("Arduino desconectado", 3000)

    def _refresh_arduino_ports(self):
        ports = ArduinoSource.list_ports()
        current = self._arduino.port
        self._arduino_widget.update_ports(ports, current)
        # Auto-select if no port set
        if not current:
            auto = ArduinoSource.find_arduino()
            if auto:
                self._arduino_widget.update_ports(ports, auto)
                self._arduino.port = auto

    # -----------------------------------------------------------
    # Mode switching
    # -----------------------------------------------------------

    def _on_mode_changed(self, index: int):
        self._mode = self._mode_combo.currentData()
        self._right_stack.setCurrentIndex(self._mode)

        if self._mode == MODE_RACE:
            self._btn_race.setText("Iniciar Carrera")
            self._btn_race.setVisible(True)
            self._btn_reset.setVisible(True)
            self._mode_label.setText("Modo: Carrera")
        else:
            self._btn_race.setVisible(False)
            self._btn_reset.setVisible(False)
            self._mode_label.setText("Modo: Contrarreloj")
            self._ranking_widget.refresh()
            if self._racing:
                self._racing = False
                self._race_log.end_race()

    # -----------------------------------------------------------
    # Frame handling
    # -----------------------------------------------------------

    def _on_frame(self, image: QImage):
        self._fps_count += 1
        self._video.update_frame(image)

        w, h = image.width(), image.height()
        ptr = image.bits()
        if ptr is not None:
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 3))
            self._last_frame_bgr = arr.copy()

    # -----------------------------------------------------------
    # Crossing dispatch - routes to race or time trial
    # -----------------------------------------------------------

    def _on_crossing(self, car_id: int, source: str):
        if self._mode == MODE_TIME_TRIAL:
            self._on_tt_crossing(car_id, source)
        else:
            self._on_race_crossing(car_id, source)

    # --- Race mode crossing ---

    def _on_race_crossing(self, car_id: int, source: str):
        event = self._race.process_crossing(car_id, source)
        if event is None:
            return

        if event.event == EventType.START:
            self._standings.show_event(
                f"START: {event.car_name} en pista"
            )
        elif event.event == EventType.LAP:
            self._standings.show_event(
                f"VUELTA {event.lap_number}: {event.car_name} - "
                f"{format_time(event.lap_time_ms)}"
            )
            self._race_view.add_event(event)

        if self._race_log.active:
            self._race_log.record_event(event)

        self._standings.update_standings(self._race.get_standings())

    # --- Time trial crossing ---

    def _on_tt_crossing(self, car_id: int, source: str):
        event = self._time_trial.process_crossing(car_id, source)
        if event is None:
            return

        if event.event == EventType.START:
            self._tt_widget.on_start()
        elif event.event == EventType.LAP:
            self._tt_widget.on_lap(
                event.lap_number,
                event.lap_time_ms,
                self._time_trial.total_time_ms,
                self._time_trial.best_lap_ms,
            )
            if self._time_trial.finished:
                self._tt_widget.on_finish(self._time_trial.total_time_ms)

    def _on_tt_name_submitted(self, player_name: str):
        entry = self._time_trial.submit_to_ranking(player_name)
        pos = entry.get("position", "?")
        total = format_time(entry["total_ms"])
        self._status.showMessage(
            f"Guardado! {player_name} - {total} - Posicion #{pos}", 5000
        )
        self._ranking_widget.refresh()
        self._ranking_widget.highlight_player(player_name)
        self._tt_tabs.setCurrentIndex(1)  # Switch to ranking tab

    def _on_tt_reset(self):
        self._time_trial.reset()

    # -----------------------------------------------------------
    # Car registration
    # -----------------------------------------------------------

    def _on_register_car(self):
        self._car_setup_dialog = CarSetupDialog(MAX_CARS, self)
        self._car_setup_dialog.car_registered.connect(self._do_register_car)
        self._car_setup_dialog._sample_btn.clicked.connect(
            lambda: self._video.set_mode("color_sample")
        )
        self._car_setup_dialog.show()

    def _do_register_car(self, slot: int, name: str, hsv_lower: np.ndarray,
                         hsv_upper: np.ndarray, display_color: tuple):
        self._race.register_car(slot, name, hsv_lower, hsv_upper, display_color)
        self._sync_cars_to_camera()
        active = len(self._race.get_active_cars())
        self._cars_label.setText(f"Autos: {active}/6")
        self._standings.update_standings(self._race.get_standings())
        self._save_config()

    def _on_color_sample(self, x: int, y: int):
        if self._last_frame_bgr is None:
            return
        lower, upper, color = ColorCalibrator.sample_color(self._last_frame_bgr, (x, y))
        if self._car_setup_dialog:
            self._car_setup_dialog.set_sampled_color(lower, upper, color)

    # -----------------------------------------------------------
    # Finish line
    # -----------------------------------------------------------

    def _on_define_finish_line(self):
        self._fl_points.clear()
        self._video.set_mode("finish_line")
        self._status.showMessage(
            "Haz clic en dos puntos para definir la linea de meta", 5000
        )

    def _on_fl_point(self, x: int, y: int):
        self._fl_points.append((x, y))
        if len(self._fl_points) == 1:
            self._status.showMessage(
                f"Punto 1: ({x}, {y}) - Haz clic en el segundo punto"
            )
        elif len(self._fl_points) >= 2:
            self._finish_line = FinishLine(self._fl_points[0], self._fl_points[1])
            self._camera.set_finish_line(self._finish_line)
            self._video.set_mode("normal")
            self._status.showMessage("Linea de meta definida", 3000)
            self._save_config()

    # -----------------------------------------------------------
    # Race controls
    # -----------------------------------------------------------

    def _on_toggle_race(self):
        if not self._racing:
            if self._detection_source == SOURCE_CAMERA:
                active = self._race.get_active_cars()
                if not active:
                    QMessageBox.warning(self, "Sin autos",
                                        "Registra al menos un auto antes de iniciar.")
                    return
                if not self._finish_line.defined:
                    QMessageBox.warning(self, "Sin meta",
                                        "Define la linea de meta antes de iniciar.")
                    return

            self._racing = True
            self._race.reset()
            self._race_view.clear()

            active = self._race.get_active_cars()
            car_names = {cid: car.name for cid, car in active} if active else {0: "AUTO"}
            self._race_log.start_race(car_names)

            self._btn_race.setText("Finalizar Carrera")
            self._btn_race.setStyleSheet(
                "background-color: #5a2d2d; padding: 6px 12px; border: 1px solid #4a4a4a;"
            )
            self._standings.update_standings(self._race.get_standings())
            self._status.showMessage("Carrera iniciada", 3000)
        else:
            self._racing = False
            path = self._race_log.end_race()
            self._btn_race.setText("Iniciar Carrera")
            self._btn_race.setStyleSheet(
                "background-color: #2d5a2d; padding: 6px 12px; border: 1px solid #4a4a4a;"
            )
            if path:
                self._status.showMessage(f"Carrera guardada: {path}", 5000)

    def _on_reset(self):
        self._race.reset()
        self._race_view.clear()
        self._standings.update_standings(self._race.get_standings())
        self._standings.show_event("")
        self._status.showMessage("Contadores reiniciados", 3000)

    # -----------------------------------------------------------
    # Camera
    # -----------------------------------------------------------

    def _on_camera_changed(self, index: int):
        device = self._cam_combo.currentData()
        self._camera.stop()
        self._camera.device_index = device
        self._camera.start()

    def _sync_cars_to_camera(self):
        entries = [(i, c) for i, c in enumerate(self._race.cars) if c.active]
        self._camera.set_cars(entries)

    def _update_fps(self):
        if self._detection_source == SOURCE_CAMERA:
            self._fps_label.setText(f"FPS: {self._fps_count}")
        else:
            self._fps_label.setText("Arduino")
        self._fps_count = 0

    # -----------------------------------------------------------
    # Detection sensitivity
    # -----------------------------------------------------------

    def _on_sensitivity_changed(self, name: str):
        ColorCalibrator.set_sensitivity(name)
        self._status.showMessage(f"Sensibilidad: {name}", 3000)
        self._save_config()

    def _on_min_px_changed(self, value: int):
        # Keep slider and spinbox in sync
        if self.sender() is self._px_slider:
            self._px_spin.blockSignals(True)
            self._px_spin.setValue(value)
            self._px_spin.blockSignals(False)
        else:
            self._px_slider.blockSignals(True)
            self._px_slider.setValue(value)
            self._px_slider.blockSignals(False)
        self._camera.min_pixel_count = value
        self._status.showMessage(f"Min pixeles: {value}", 2000)
        self._save_config()

    # -----------------------------------------------------------
    # Config persistence
    # -----------------------------------------------------------

    def _save_config(self):
        config = {
            "finish_line": self._finish_line.to_dict() if self._finish_line.defined else None,
            "camera_index": self._camera.device_index,
            "sensitivity": ColorCalibrator.get_sensitivity(),
            "min_pixel_count": self._camera.min_pixel_count,
            "detection_source": self._detection_source,
            "arduino_port": self._arduino.port,
            "arduino_threshold": self._arduino_widget.threshold,
            "cars": [],
        }
        for i, car in enumerate(self._race.cars):
            if car.active:
                d = car.to_dict()
                d["slot"] = i
                config["cars"].append(d)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _load_config(self):
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        if config.get("finish_line"):
            self._finish_line = FinishLine.from_dict(config["finish_line"])
            self._camera.set_finish_line(self._finish_line)

        if config.get("camera_index") is not None:
            idx = config["camera_index"]
            self._camera.device_index = idx
            self._cam_combo.setCurrentIndex(idx)

        # Restore detection sensitivity
        if config.get("sensitivity"):
            sens = config["sensitivity"]
            ColorCalibrator.set_sensitivity(sens)
            self._sens_combo.blockSignals(True)
            self._sens_combo.setCurrentText(sens)
            self._sens_combo.blockSignals(False)

        if config.get("min_pixel_count") is not None:
            px = config["min_pixel_count"]
            self._camera.min_pixel_count = px
            self._px_slider.blockSignals(True)
            self._px_spin.blockSignals(True)
            self._px_slider.setValue(px)
            self._px_spin.setValue(px)
            self._px_slider.blockSignals(False)
            self._px_spin.blockSignals(False)

        # Restore Arduino settings
        if config.get("arduino_port"):
            self._arduino.port = config["arduino_port"]

        if config.get("arduino_threshold") is not None:
            self._arduino_widget.set_confirmed_threshold(config["arduino_threshold"])

        for car_data in config.get("cars", []):
            from ..models.car import CarColor
            slot = car_data.pop("slot", 0)
            car = CarColor.from_dict(car_data)
            self._race.register_car(
                slot, car.name, car.hsv_lower, car.hsv_upper, car.display_color
            )

        self._sync_cars_to_camera()
        active = len(self._race.get_active_cars())
        self._cars_label.setText(f"Autos: {active}/6")
        self._standings.update_standings(self._race.get_standings())

        # Restore detection source (must be last - triggers UI switch)
        source = config.get("detection_source", SOURCE_CAMERA)
        if source == SOURCE_ARDUINO:
            self._source_combo.setCurrentIndex(1)  # triggers _on_source_changed

    def closeEvent(self, event):
        self._save_config()
        if self._race_log.active:
            self._race_log.end_race()
        self._camera.stop()
        if self._arduino.isRunning():
            self._arduino.set_streaming(False)
            self._arduino.stop()
        event.accept()

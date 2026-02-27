import json
import time
import queue
import serial
import serial.tools.list_ports
from PySide6.QtCore import QThread, Signal


class ArduinoSource(QThread):
    """QThread that communicates with the LaserLapTimer Arduino firmware."""

    crossing_detected = Signal(int)     # car_id (always 0)
    ldr_value = Signal(int)             # live LDR reading
    connection_changed = Signal(bool)   # connected/disconnected
    threshold_changed = Signal(int)     # confirmed threshold from Arduino
    ready = Signal(int, int)            # baseline, threshold on startup
    error_occurred = Signal(str)        # error message
    test_result = Signal(int, int, int, bool)  # ldr_off, ldr_on, diff, laser_detected

    def __init__(self, parent=None):
        super().__init__(parent)
        self.port = ""
        self.baudrate = 115200
        self._running = False
        self._cmd_queue: queue.Queue[str] = queue.Queue()

    # ── Public API (called from main thread) ──

    def send_command(self, cmd: str):
        self._cmd_queue.put(cmd)

    def set_threshold(self, value: int):
        self.send_command(f"THRESHOLD {value}")

    def set_laser(self, on: bool):
        self.send_command(f"LASER {'ON' if on else 'OFF'}")

    def set_streaming(self, on: bool):
        self.send_command(f"STREAM {'ON' if on else 'OFF'}")

    def request_ldr(self):
        self.send_command("LDR")

    def request_reset(self):
        self.send_command("RESET")

    def request_test(self):
        self.send_command("TEST")

    def stop(self):
        self._running = False
        self.wait(3000)

    # ── Port detection ──

    @staticmethod
    def list_ports() -> list[tuple[str, str]]:
        ports = serial.tools.list_ports.comports()
        return [(p.device, p.description) for p in sorted(ports)]

    @staticmethod
    def find_arduino() -> str | None:
        for port, desc in ArduinoSource.list_ports():
            low = desc.lower()
            if any(kw in low for kw in ("ch340", "ch341", "arduino", "mega", "usb-serial")):
                return port
        return None

    # ── Thread run loop ──

    def run(self):
        self._running = True
        ser = None

        while self._running:
            # Connect
            if ser is None or not ser.is_open:
                ser = self._try_connect()
                if ser is None:
                    self.connection_changed.emit(False)
                    # Wait before retry
                    for _ in range(20):
                        if not self._running:
                            return
                        time.sleep(0.1)
                    continue

            # Read & process
            try:
                # Drain command queue
                while not self._cmd_queue.empty():
                    try:
                        cmd = self._cmd_queue.get_nowait()
                        ser.write((cmd + "\n").encode("utf-8"))
                    except queue.Empty:
                        break

                # Read line (with timeout from serial config)
                if ser.in_waiting > 0:
                    raw = ser.readline()
                    if raw:
                        self._process_line(raw.decode("utf-8", errors="replace").strip())

            except (serial.SerialException, OSError):
                self.connection_changed.emit(False)
                self.error_occurred.emit("Conexion perdida con Arduino")
                try:
                    ser.close()
                except Exception:
                    pass
                ser = None

            time.sleep(0.01)  # Prevent busy loop

        # Cleanup
        if ser and ser.is_open:
            try:
                ser.write(b"STREAM OFF\n")
                time.sleep(0.05)
                ser.close()
            except Exception:
                pass

    def _try_connect(self) -> serial.Serial | None:
        if not self.port:
            return None
        try:
            ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
            )
            # Arduino resets on DTR - wait for READY event
            start = time.time()
            while time.time() - start < 5.0:
                if not self._running:
                    ser.close()
                    return None
                if ser.in_waiting > 0:
                    raw = ser.readline().decode("utf-8", errors="replace").strip()
                    if raw:
                        try:
                            msg = json.loads(raw)
                            if msg.get("event") == "READY":
                                data = msg.get("data", {})
                                bl = data.get("baseline", 0)
                                th = data.get("threshold", 0)
                                self.ready.emit(bl, th)
                                self.threshold_changed.emit(th)
                                self.connection_changed.emit(True)
                                return ser
                        except json.JSONDecodeError:
                            pass
                time.sleep(0.05)
            # Timeout waiting for READY - still return connection
            self.connection_changed.emit(True)
            return ser
        except (serial.SerialException, OSError) as e:
            self.error_occurred.emit(f"No se pudo abrir {self.port}: {e}")
            return None

    def _process_line(self, line: str):
        if not line:
            return
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            return

        event = msg.get("event", "")
        data = msg.get("data", {})

        if event == "LDR_CUT":
            self.crossing_detected.emit(0)
            val = data.get("value", 0)
            self.ldr_value.emit(val)

        elif event == "LDR_STREAM":
            self.ldr_value.emit(data.get("value", 0))

        elif event == "LDR_READ":
            self.ldr_value.emit(data.get("value", 0))

        elif event == "THRESHOLD_SET":
            self.threshold_changed.emit(data.get("threshold", 0))

        elif event == "READY":
            bl = data.get("baseline", 0)
            th = data.get("threshold", 0)
            self.ready.emit(bl, th)
            self.threshold_changed.emit(th)

        elif event == "TEST_RESULT":
            self.test_result.emit(
                data.get("ldr_off", 0),
                data.get("ldr_on", 0),
                data.get("diff", 0),
                data.get("laser_detected", False),
            )

        elif event == "ERROR":
            self.error_occurred.emit(data.get("msg", "Error desconocido"))

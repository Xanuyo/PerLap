import sys
from PySide6.QtWidgets import QApplication
from perlap.models.race import RaceManager
from perlap.detection.camera import CameraSource
from perlap.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    race = RaceManager()
    camera = CameraSource(device_index=0)

    window = MainWindow(race_manager=race, camera_source=camera)
    camera.start()
    window.show()

    ret = app.exec()
    camera.stop()
    sys.exit(ret)


if __name__ == "__main__":
    main()

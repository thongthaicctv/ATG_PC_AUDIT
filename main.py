import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from core.logger import configure_logging
from ui.main_window import MainWindow
from core.resource_utils import resource_path


def main() -> int:
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("ATG PC AUDIT")
    app.setApplicationDisplayName("ATG PC AUDIT")
    app.setWindowIcon(QIcon(str(resource_path("assets/app.ico"))))
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

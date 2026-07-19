import ctypes,sys
from PyQt5.QtWidgets import QApplication
from recovery_tool.recovery_window import RecoveryWindow


def main():
    if sys.platform!="win32":raise SystemExit("Recovery tool chỉ hỗ trợ Windows.")
    app=QApplication(sys.argv);window=RecoveryWindow();window.show();return app.exec_()


if __name__=="__main__":raise SystemExit(main())

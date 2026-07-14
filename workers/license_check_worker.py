from PyQt5.QtCore import QThread, pyqtSignal


class LicenseCheckWorker(QThread):
    status_changed = pyqtSignal(str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)
    def __init__(self, client, device_id, parent=None):super().__init__(parent);self.client=client;self.device_id=device_id
    def run(self):
        try:self.status_changed.emit("Đang kiểm tra cấp phép...");self.completed.emit(self.client.check(self.device_id,True))
        except Exception as exc:self.failed.emit(str(exc))

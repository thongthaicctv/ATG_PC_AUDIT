from PyQt5.QtCore import QThread,pyqtSignal
from core.gmail_launcher import open_gmail


class EmailPrepareWorker(QThread):
    progress_changed=pyqtSignal(int);status_changed=pyqtSignal(str);prepared=pyqtSignal();failed=pyqtSignal(str)
    def run(self):
        try:self.progress_changed.emit(50);self.status_changed.emit("Đang chuẩn bị nội dung");open_gmail();self.progress_changed.emit(100);self.prepared.emit()
        except Exception as exc:self.failed.emit(str(exc))

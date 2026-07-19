from PyQt5.QtCore import QThread,pyqtSignal
from core.zalo_launcher import launch_zalo


class ZaloPrepareWorker(QThread):
    progress_changed=pyqtSignal(int);status_changed=pyqtSignal(str);prepared=pyqtSignal();fallback_required=pyqtSignal(str);failed=pyqtSignal(str)
    def __init__(self,executable=None,assisted=True,parent=None):super().__init__(parent);self.executable=executable;self.assisted=assisted
    def run(self):
        try:
            self.progress_changed.emit(20);self.status_changed.emit("Đang tìm Zalo Desktop");launch_zalo(self.executable);self.progress_changed.emit(50)
            if self.assisted:
                from pywinauto.keyboard import send_keys
                self.status_changed.emit("Đang mở vùng tìm kiếm người nhận");send_keys("^f",pause=.2);send_keys("^v",pause=.2)
            self.progress_changed.emit(100);self.prepared.emit()
        except FileNotFoundError as exc:self.fallback_required.emit(str(exc))
        except Exception as exc:self.failed.emit(str(exc))

from PyQt5.QtCore import QThread,pyqtSignal


class AggregateSyncWorker(QThread):
    progress_changed=pyqtSignal(int,str);completed=pyqtSignal(object);failed=pyqtSignal(str)
    def __init__(self,service,parent=None):super().__init__(parent);self.service=service
    def run(self):
        try:self.completed.emit(self.service.sync(lambda current,total:self.progress_changed.emit(int(current*100/max(total,1)),f"Đồng bộ change_seq {current}/{total}")))
        except Exception as exc:self.failed.emit(str(exc))


from PyQt5.QtCore import QThread,pyqtSignal


class SubmitAuditWorker(QThread):
    status_changed=pyqtSignal(str);completed=pyqtSignal(object);failed=pyqtSignal(str)
    def __init__(self,service,result,parent=None):super().__init__(parent);self.service=service;self.result=result
    def run(self):
        try:self.status_changed.emit("ĐANG CẬP NHẬT");self.completed.emit(self.service.submit(self.result))
        except Exception as exc:self.failed.emit(str(exc))


from PyQt5.QtCore import QThread,pyqtSignal


class RetryQueueWorker(QThread):
    completed=pyqtSignal(object);failed=pyqtSignal(str)
    def __init__(self,service,due_only=False,parent=None):super().__init__(parent);self.service=service;self.due_only=due_only
    def run(self):
        try:self.completed.emit(self.service.retry(self.due_only))
        except Exception as exc:self.failed.emit(str(exc))


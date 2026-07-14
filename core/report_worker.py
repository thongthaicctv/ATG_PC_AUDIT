from PyQt5.QtCore import QThread,pyqtSignal

class TaskWorker(QThread):
    progress=pyqtSignal(int,str);completed=pyqtSignal(object);failed=pyqtSignal(str)
    def __init__(self,fn,*args,parent=None,**kwargs):super().__init__(parent);self.fn=fn;self.args=args;self.kwargs=kwargs
    def run(self):
        try:self.progress.emit(10,"Đang xử lý dữ liệu...");result=self.fn(*self.args,**self.kwargs);self.progress.emit(100,"Hoàn thành");self.completed.emit(result)
        except Exception as e:self.failed.emit(str(e))

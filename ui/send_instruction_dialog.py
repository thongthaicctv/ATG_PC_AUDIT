from pathlib import Path
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QDialog,QLabel,QPushButton,QVBoxLayout


class SendInstructionDialog(QDialog):
    def __init__(self,title,text,file_path,parent=None):
        super().__init__(parent);self.setWindowTitle(title);self.setMinimumWidth(560);layout=QVBoxLayout(self);label=QLabel(text);label.setWordWrap(True);layout.addWidget(label)
        open_btn=QPushButton("MỞ FILE CSV");open_btn.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(file_path).parent))));layout.addWidget(open_btn);close=QPushButton("ĐÓNG");close.clicked.connect(self.accept);layout.addWidget(close)

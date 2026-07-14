from PyQt5.QtCore import QTimer,Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication,QDialog,QHBoxLayout,QLabel,QLineEdit,QProgressBar,QPushButton,QVBoxLayout

from ui.license_detail_dialog import LicenseDetailDialog
from workers.license_check_worker import LicenseCheckWorker


class LicenseActivationDialog(QDialog):
    def __init__(self,identity,client,current=None,parent=None):
        super().__init__(parent);self.identity=identity;self.client=client;self.result=current;self.worker=None;self.setWindowTitle("KÍCH HOẠT TÍNH NĂNG TỔNG HỢP");self.setMinimumWidth(620)
        layout=QVBoxLayout(self);title=QLabel("TÍNH NĂNG TỔNG HỢP DỮ LIỆU TOÀN CÔNG TY CHƯA ĐƯỢC KÍCH HOẠT");title.setWordWrap(True);title.setStyleSheet("font-size:16px;font-weight:bold;color:#a61b1b");layout.addWidget(title)
        help_text=QLabel("Vui lòng sao chép DEVICE_ID bên dưới và gửi cho quản trị hệ thống để được cấp quyền trên Google Sheet.");help_text.setWordWrap(True);layout.addWidget(help_text)
        row=QHBoxLayout();self.device=QLineEdit(identity.device_id);self.device.setReadOnly(True);self.device.setAlignment(Qt.AlignCenter);self.device.setFont(QFont("Consolas",12));row.addWidget(self.device,1);self.copy_btn=QPushButton("SAO CHÉP DEVICE ID");self.copy_btn.clicked.connect(self.copy_id);row.addWidget(self.copy_btn);layout.addLayout(row)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status);self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.hide();layout.addWidget(self.progress)
        buttons=QHBoxLayout();self.check_btn=QPushButton("KIỂM TRA KÍCH HOẠT");self.check_btn.clicked.connect(self.check);self.detail_btn=QPushButton("XEM CHI TIẾT");self.detail_btn.clicked.connect(self.detail);self.continue_btn=QPushButton("TIẾP TỤC MỞ TỔNG HỢP");self.continue_btn.clicked.connect(self.accept);self.continue_btn.hide();close=QPushButton("ĐÓNG");close.clicked.connect(self.reject)
        for b in (self.check_btn,self.detail_btn,self.continue_btn,close):buttons.addWidget(b)
        layout.addLayout(buttons);self.show_result(current)
    def copy_id(self):
        QApplication.clipboard().setText(self.identity.device_id);self.copy_btn.setText("ĐÃ SAO CHÉP");self.status.setText("Đã sao chép DEVICE_ID");QTimer.singleShot(2000,lambda:self.copy_btn.setText("SAO CHÉP DEVICE ID"))
    def check(self):
        self.check_btn.setEnabled(False);self.progress.show();self.status.setText("Đang kiểm tra cấp phép...");self.worker=LicenseCheckWorker(self.client,self.identity.device_id,self);self.worker.completed.connect(self.checked);self.worker.failed.connect(self.failed);self.worker.start()
    def checked(self,result):self.result=result;self.progress.hide();self.check_btn.setEnabled(True);self.show_result(result)
    def failed(self,message):self.progress.hide();self.check_btn.setEnabled(True);self.status.setText(message)
    def show_result(self,result):
        if not result:return
        self.status.setText(result.message);self.continue_btn.setVisible(result.is_valid)
        self.status.setStyleSheet("color:#176b32;font-weight:bold" if result.is_valid else "color:#a61b1b;font-weight:bold")
    def detail(self):
        if self.result:LicenseDetailDialog(self.result,self).exec_()

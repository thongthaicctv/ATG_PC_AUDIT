from pathlib import Path
from PyQt5.QtWidgets import QCheckBox,QDialog,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QProgressBar,QPushButton,QTextEdit,QVBoxLayout
from core.clipboard_manager import copy_email,copy_message,copy_subject
from core.gmail_launcher import reveal_file,valid_email
from core.send_history import record_send
from core.send_settings import load_send_settings,save_send_settings
from workers.email_prepare_worker import EmailPrepareWorker


class EmailSendDialog(QDialog):
    def __init__(self,result,file_path,parent=None):
        super().__init__(parent);self.result=result;self.file=Path(file_path);self.worker=None;self.setWindowTitle("CHUẨN BỊ GỬI QUA GMAIL");self.setMinimumSize(680,500);settings=load_send_settings();m=result.metadata;c=result.computer
        layout=QVBoxLayout(self);form=QFormLayout();self.email=QLineEdit(settings.get("admin_email","") if settings.get("remember_admin_email") else "");self.email.setPlaceholderText("Ví dụ: quantri@congty.vn");self.subject=QLineEdit(f"Thông tin máy tính {m.get('asset_code','')} - {c.get('computer_name','')}")
        office=", ".join(dict.fromkeys(x.get("activation_status","") for x in result.office_licenses));self.message=QTextEdit(f"Kính gửi quản trị viên,\n\nTôi gửi file kiểm tra máy tính với các thông tin:\n\nMã tài sản: {m.get('asset_code','')}\nTên máy: {c.get('computer_name','')}\nNgười sử dụng: {m.get('user','')}\nPhòng ban: {m.get('department','')}\nVị trí: {m.get('location','')}\nNgày kiểm tra: {m.get('audit_date_display') or m.get('audit_date','')}\nKết quả Windows 11: {result.windows11.get('overall','')}\nBản quyền Windows: {result.windows_license.get('activation_status','')}\nBản quyền Office: {office}\n\nFile CSV cần đính kèm: {self.file.name}\n\nTrân trọng.")
        form.addRow("Email người nhận",self.email);form.addRow("Tiêu đề",self.subject);form.addRow("Nội dung",self.message);layout.addLayout(form);self.remember=QCheckBox("Ghi nhớ email quản trị");self.remember.setChecked(bool(settings.get("remember_admin_email")));layout.addWidget(self.remember);self.progress=QProgressBar();self.progress.hide();layout.addWidget(self.progress);self.status=QLabel();layout.addWidget(self.status)
        buttons=QHBoxLayout();items=[("MỞ GMAIL",self.open_gmail),("SAO CHÉP TIÊU ĐỀ",lambda:self.copy(self.subject.text(),"Đã sao chép tiêu đề.")),("SAO CHÉP NỘI DUNG",lambda:self.copy(self.message.toPlainText(),"Đã sao chép nội dung.")),("MỞ THƯ MỤC CHỨA FILE",lambda:reveal_file(self.file)),("HỦY",self.reject)]
        for text,fn in items:b=QPushButton(text);b.clicked.connect(fn);buttons.addWidget(b)
        layout.addLayout(buttons)
    def copy(self,text,status):copy_message(text);self.status.setText(status)
    def open_gmail(self):
        address=self.email.text().strip()
        if not valid_email(address):QMessageBox.warning(self,"Email","Địa chỉ email người nhận không hợp lệ.");self.email.setFocus();return
        save_send_settings(remember_admin_email=self.remember.isChecked(),admin_email=address if self.remember.isChecked() else "")
        copy_message(self.message.toPlainText());reveal_file(self.file);self.progress.setRange(0,100);self.progress.show();self.worker=EmailPrepareWorker(self);self.worker.progress_changed.connect(self.progress.setValue);self.worker.status_changed.connect(self.status.setText);self.worker.prepared.connect(lambda:self.prepared(address));self.worker.failed.connect(lambda e:QMessageBox.warning(self,"Gmail",e));self.worker.start()
    def prepared(self,address):
        record_send(self.result.audit_id,self.result.metadata.get("asset_code"),self.result.computer.get("computer_name"),"GMAIL",self.file,address,"GMAIL_OPENED");self.status.setText("Gmail đã mở. Hãy soạn thư, đính kèm file đang được chọn, kiểm tra và tự bấm Gửi.")

from pathlib import Path
from PyQt5.QtWidgets import QCheckBox,QDialog,QFileDialog,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QProgressBar,QPushButton,QTextEdit,QVBoxLayout
from core.clipboard_manager import copy_message,copy_phone
from core.gmail_launcher import reveal_file
from core.send_history import record_send
from core.send_settings import load_send_settings,save_send_settings
from core.zalo_launcher import normalize_vietnam_phone
from workers.zalo_prepare_worker import ZaloPrepareWorker


class ZaloSendDialog(QDialog):
    def __init__(self,result,file_path,parent=None):
        super().__init__(parent);self.result=result;self.file=Path(file_path);self.worker=None;self.zalo_exe=None;self.setWindowTitle("CHUẨN BỊ GỬI QUA ZALO");self.setMinimumSize(680,500);settings=load_send_settings();m=result.metadata;c=result.computer
        layout=QVBoxLayout(self);form=QFormLayout();self.phone=QLineEdit(settings.get("zalo_phone","") if settings.get("remember_zalo_phone") else "");self.phone.setPlaceholderText("Ví dụ: 0912345678");self.message=QTextEdit(f"Kính gửi quản trị viên,\n\nTôi gửi file kiểm tra máy tính:\n- Mã tài sản: {m.get('asset_code','')}\n- Tên máy: {c.get('computer_name','')}\n- Người sử dụng: {m.get('user','')}\n- Phòng ban: {m.get('department','')}\n- Ngày kiểm tra: {m.get('audit_date_display') or m.get('audit_date','')}\n- Windows 11: {result.windows11.get('overall','')}\n\nFile đính kèm: {self.file.name}\n\nVui lòng kiểm tra và nhập vào hệ thống tổng hợp.")
        form.addRow("Số điện thoại người nhận",self.phone);form.addRow("Nội dung gửi",self.message);layout.addLayout(form);self.remember=QCheckBox("Ghi nhớ số Zalo quản trị cho lần sau");self.remember.setChecked(bool(settings.get("remember_zalo_phone")));layout.addWidget(self.remember);self.assisted=QCheckBox("Tự động hỗ trợ thao tác trên Zalo Desktop");self.assisted.setChecked(bool(settings.get("zalo_assisted_mode",True)));layout.addWidget(self.assisted);self.progress=QProgressBar();self.progress.hide();layout.addWidget(self.progress);self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        buttons=QHBoxLayout();items=[("MỞ ZALO VÀ CHUẨN BỊ",self.prepare),("SAO CHÉP NỘI DUNG",lambda:self.copy(self.message.toPlainText(),"Đã sao chép nội dung.")),("MỞ THƯ MỤC CHỨA FILE",lambda:reveal_file(self.file)),("HỦY",self.reject)]
        for text,fn in items:b=QPushButton(text);b.clicked.connect(fn);buttons.addWidget(b)
        layout.addLayout(buttons)
    def copy(self,text,status):copy_message(text);self.status.setText(status)
    def prepare(self):
        try:phone=normalize_vietnam_phone(self.phone.text())
        except ValueError:QMessageBox.warning(self,"Zalo","Số điện thoại không hợp lệ.\nVui lòng nhập số điện thoại người nhận, ví dụ 0912345678.");self.phone.setFocus();return
        save_send_settings(remember_zalo_phone=self.remember.isChecked(),zalo_phone=phone if self.remember.isChecked() else "",zalo_assisted_mode=self.assisted.isChecked());copy_phone(phone);reveal_file(self.file);self.progress.setRange(0,100);self.progress.show();self.worker=ZaloPrepareWorker(self.zalo_exe,self.assisted.isChecked(),self);self.worker.progress_changed.connect(self.progress.setValue);self.worker.status_changed.connect(self.status.setText);self.worker.prepared.connect(lambda:self.prepared(phone));self.worker.fallback_required.connect(lambda e:self.fallback(phone,e));self.worker.failed.connect(lambda e:self.fallback(phone,e));self.worker.start()
    def prepared(self,phone):
        copy_message(self.message.toPlainText());record_send(self.result.audit_id,self.result.metadata.get("asset_code"),self.result.computer.get("computer_name"),"ZALO",self.file,phone,"ZALO_PREPARED");self.status.setText("Đã mở Zalo và chuẩn bị nội dung. Hãy chọn đúng người nhận, dán nội dung, kéo file đang chọn vào Zalo rồi tự bấm Gửi.")
    def fallback(self,phone,error):
        record_send(self.result.audit_id,self.result.metadata.get("asset_code"),self.result.computer.get("computer_name"),"ZALO",self.file,phone,"ZALO_MANUAL_FALLBACK",error);self.status.setText(str(error)+"\nĐã sao chép số điện thoại và chọn file trong Explorer. Bạn có thể chọn Zalo.exe hoặc gửi thủ công.");path,_=QFileDialog.getOpenFileName(self,"Chọn Zalo.exe",filter="Zalo (Zalo.exe)");self.zalo_exe=path or None

import shutil
from pathlib import Path
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QButtonGroup,QDialog,QFileDialog,QFormLayout,QGroupBox,QHBoxLayout,QLabel,QMessageBox,QPushButton,QRadioButton,QVBoxLayout
from core.send_history import record_send
from ui.email_send_dialog import EmailSendDialog
from ui.zalo_send_dialog import ZaloSendDialog


class SendDataDialog(QDialog):
    def __init__(self,result,file_path,parent=None):
        super().__init__(parent);self.result=result;self.file=Path(file_path);self.setWindowTitle("GỬI DỮ LIỆU CHO QUẢN TRỊ");self.setMinimumWidth(700);layout=QVBoxLayout(self);m=result.metadata;c=result.computer;form=QFormLayout()
        for title,value in (("Mã tài sản",m.get("asset_code")),("Tên máy",c.get("computer_name")),("Người sử dụng",m.get("user")),("Phòng ban",m.get("department")),("Ngày kiểm tra",m.get("audit_date_display") or m.get("audit_date")),("Tên file CSV",self.file.name),("Dung lượng file",f"{self.file.stat().st_size/1024:.1f} KB"),("Đường dẫn",str(self.file))):form.addRow(title+":",QLabel(str(value or "-")))
        layout.addLayout(form);warning=QLabel("File CSV chứa thông tin cấu hình máy tính, địa chỉ MAC, IP và trạng thái bản quyền. Vui lòng kiểm tra đúng người nhận trước khi gửi.");warning.setWordWrap(True);warning.setStyleSheet("background:#fff3cd;padding:8px;color:#725c00");layout.addWidget(warning);self.group=QButtonGroup(self);self.local=QRadioButton("LƯU FILE VỀ MÁY TÍNH — Lưu hoặc sao chép CSV đến vị trí lựa chọn");self.zalo=QRadioButton("GỬI QUA ZALO — Mở Zalo Desktop và chuẩn bị nội dung/file");self.gmail=QRadioButton("GỬI QUA GMAIL — Mở Gmail và chọn sẵn file cần đính kèm");self.local.setChecked(True)
        for radio in (self.local,self.zalo,self.gmail):self.group.addButton(radio);layout.addWidget(radio)
        row=QHBoxLayout();go=QPushButton("TIẾP TỤC");go.clicked.connect(self.continue_method);cancel=QPushButton("HỦY");cancel.clicked.connect(self.reject);row.addStretch();row.addWidget(go);row.addWidget(cancel);layout.addLayout(row)
    def continue_method(self):
        if self.local.isChecked():self.save_local()
        elif self.zalo.isChecked():ZaloSendDialog(self.result,self.file,self).exec_()
        else:EmailSendDialog(self.result,self.file,self).exec_()
    def save_local(self):
        target,_=QFileDialog.getSaveFileName(self,"Chọn vị trí lưu file CSV",str(Path.home()/"Documents"/self.file.name),"CSV (*.csv)")
        if not target:return
        path=Path(target)
        if path.exists():
            answer=QMessageBox.question(self,"File đã tồn tại","File đã tồn tại. Chọn Yes để ghi đè, No để tạo bản sao mới hoặc Cancel để hủy.",QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
            if answer==QMessageBox.Cancel:return
            if answer==QMessageBox.No:
                base=path.with_suffix("");n=1
                while path.exists():path=base.with_name(f"{base.name}_{n:02d}").with_suffix(".csv");n+=1
        path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(self.file,path);record_send(self.result.audit_id,self.result.metadata.get("asset_code"),self.result.computer.get("computer_name"),"LOCAL",path,"","FILE_SAVED");QMessageBox.information(self,"Đã lưu",f"Đã lưu file dữ liệu thành công.\n\nTên file: {path.name}\nVị trí: {path}")

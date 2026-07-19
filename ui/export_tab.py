from pathlib import Path
from PyQt5.QtCore import QUrl,pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QCheckBox,QFileDialog,QFormLayout,QGroupBox,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPushButton,QVBoxLayout,QWidget
from core.csv_exporter import default_export_directory


class ExportTab(QWidget):
    export_requested=pyqtSignal();send_requested=pyqtSignal();retry_requested=pyqtSignal();auto_changed=pyqtSignal(bool)
    def __init__(self):
        super().__init__();self.last_file=None;layout=QVBoxLayout(self);info=QGroupBox("Thông tin kết quả");self.form=QFormLayout(info);self.labels={}
        fields=(("asset","Mã tài sản"),("computer","Tên máy"),("serial","Serial Number"),("user","Người sử dụng"),("employee_code","Mã nhân viên"),("department","Phòng ban"),("date","Ngày kiểm tra"),("scan","Trạng thái quét"),("win11","Windows 11"),("windows_license","Bản quyền Windows"),("office","Bản quyền Office"),("mac","MAC chính"),("ip","IP hiện tại"))
        for key,title in fields:label=QLabel("Chưa quét");self.form.addRow(title+":",label);self.labels[key]=label
        layout.addWidget(info);folder_box=QGroupBox("Thư mục lưu CSV tự động sau khi quét");row=QHBoxLayout(folder_box);self.folder=QLineEdit(str(default_export_directory()));choose=QPushButton("CHỌN THƯ MỤC");choose.clicked.connect(self.choose_folder);open_btn=QPushButton("MỞ THƯ MỤC");open_btn.clicked.connect(self.open_folder);row.addWidget(self.folder,1);row.addWidget(choose);row.addWidget(open_btn);layout.addWidget(folder_box)
        self.auto=QCheckBox("Tự động cập nhật cho quản trị sau khi quét thành công");self.auto.setChecked(False);self.auto.toggled.connect(self.auto_changed.emit);layout.addWidget(self.auto)
        sync_box=QGroupBox("TRẠNG THÁI CẬP NHẬT");sync_form=QFormLayout(sync_box);self.sync_labels={}
        for key,title in (("connection","Kết nối API"),("device","Trạng thái thiết bị"),("last_time","Cập nhật gần nhất"),("audit_id","Audit ID gần nhất"),("queue","Bản ghi đang chờ"),("message","Thông báo máy chủ"),("device_id","DEVICE_ID")):
            label=QLabel("CHƯA CẬP NHẬT");label.setWordWrap(True);sync_form.addRow(title+":",label);self.sync_labels[key]=label
        layout.addWidget(sync_box)
        actions=QHBoxLayout();self.export_btn=QPushButton("CẬP NHẬT CHO QUẢN TRỊ");self.export_btn.setEnabled(False);self.export_btn.clicked.connect(self.send_requested.emit);csv=QPushButton("LƯU FILE CSV");csv.clicked.connect(self.export_requested.emit);retry=QPushButton("GỬI LẠI DỮ LIỆU CHỜ");retry.clicked.connect(self.retry_requested.emit);open_result=QPushButton("MỞ THƯ MỤC KẾT QUẢ");open_result.clicked.connect(self.open_folder)
        for button in (self.export_btn,csv,retry,open_result):actions.addWidget(button)
        layout.addLayout(actions);self.status=QLabel("Chưa có dữ liệu cập nhật.");self.status.setWordWrap(True);layout.addWidget(self.status);layout.addStretch()
    def choose_folder(self):
        path=QFileDialog.getExistingDirectory(self,"Chọn thư mục lưu CSV",self.folder.text())
        if path:self.folder.setText(path)
    def open_folder(self):Path(self.folder.text()).mkdir(parents=True,exist_ok=True);QDesktopServices.openUrl(QUrl.fromLocalFile(self.folder.text()))
    def set_result(self,result):
        m,c=result.metadata,result.computer;primary=next((x for x in result.network_adapters if x.get("interface_index")==result.primary_adapter_index),{})
        values={"asset":m.get("asset_code"),"computer":c.get("computer_name"),"serial":c.get("serial_number"),"user":m.get("user"),"employee_code":m.get("employee_code"),"department":m.get("department"),"date":m.get("audit_date_display") or m.get("audit_date"),"scan":"Đã hoàn thành kiểm tra máy tính","win11":result.windows11.get("overall"),"windows_license":result.windows_license.get("activation_status"),"office":", ".join(dict.fromkeys(x.get("activation_status","") for x in result.office_licenses)),"mac":primary.get("mac_address"),"ip":", ".join(primary.get("ipv4",[]))}
        for key,label in self.labels.items():label.setText(str(values.get(key) or "Không có"))
        self.export_btn.setEnabled(bool(str(m.get("asset_code") or "").strip() and str(c.get("computer_name") or "").strip()))
    def exported(self,path):self.last_file=path;self.status.setText(f"Đã tự động lưu CSV: {path}")
    def set_sync_status(self,state,message="",device_id="",queue_count=0,audit_id="",server_time=""):
        success=("CREATED","UPDATED","ALREADY_EXISTS","HISTORY_ONLY","CONFLICT_RECORDED")
        self.sync_labels["connection"].setText("Đã kết nối" if state in success else "Không kết nối" if state in ("NETWORK_ERROR","TIMEOUT","SSL_ERROR","NOT_CONFIGURED") else "Đang xử lý")
        self.sync_labels["device"].setText({"DEVICE_PENDING":"THIẾT BỊ CHỜ PHÊ DUYỆT","DEVICE_BLOCKED":"THIẾT BỊ BỊ KHÓA","DEVICE_REVOKED":"THIẾT BỊ ĐÃ THU HỒI"}.get(state,"ACTIVE" if state in success else state));self.sync_labels["last_time"].setText(server_time or "Chưa có");self.sync_labels["audit_id"].setText(audit_id or "Chưa có");self.sync_labels["queue"].setText(str(queue_count));self.sync_labels["message"].setText(message or state);self.sync_labels["device_id"].setText(device_id or "Chưa có")

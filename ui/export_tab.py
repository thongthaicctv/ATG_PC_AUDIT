from pathlib import Path
from PyQt5.QtCore import QUrl,pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QCheckBox,QFileDialog,QFormLayout,QGroupBox,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPushButton,QVBoxLayout,QWidget
from core.csv_exporter import default_export_directory

class ExportTab(QWidget):
    export_requested=pyqtSignal();auto_changed=pyqtSignal(bool)
    def __init__(self):
        super().__init__();self.last_file=None;layout=QVBoxLayout(self);info=QGroupBox("Thông tin kết quả");self.form=QFormLayout(info);self.labels={}
        for key,title in [("asset","Mã tài sản"),("computer","Tên máy"),("serial","Serial Number"),("user","Người sử dụng"),("department","Phòng ban"),("date","Ngày kiểm tra"),("scan","Trạng thái quét"),("win11","Windows 11"),("windows_license","Bản quyền Windows"),("office","Bản quyền Office"),("mac","MAC chính"),("ip","IP hiện tại")]:label=QLabel("Chưa quét");self.form.addRow(title+":",label);self.labels[key]=label
        layout.addWidget(info);folder_box=QGroupBox("Thư mục xuất");row=QHBoxLayout(folder_box);self.folder=QLineEdit(str(default_export_directory()));choose=QPushButton("CHỌN THƯ MỤC");choose.clicked.connect(self.choose_folder);open_btn=QPushButton("MỞ THƯ MỤC");open_btn.clicked.connect(self.open_folder);row.addWidget(self.folder,1);row.addWidget(choose);row.addWidget(open_btn);layout.addWidget(folder_box)
        self.auto=QCheckBox("Tự động tạo file CSV sau khi quét thành công");self.auto.setChecked(True);self.auto.toggled.connect(self.auto_changed.emit);layout.addWidget(self.auto)
        actions=QHBoxLayout();self.export_btn=QPushButton("XUẤT CSV GỬI QUẢN TRỊ");self.export_btn.setEnabled(False);self.export_btn.clicked.connect(self.export_requested.emit);again=QPushButton("XUẤT LẠI");again.clicked.connect(self.export_requested.emit);open_result=QPushButton("MỞ THƯ MỤC KẾT QUẢ");open_result.clicked.connect(self.open_folder);check=QPushButton("KIỂM TRA FILE VỪA XUẤT");check.clicked.connect(self.check_file)
        for b in (self.export_btn,again,open_result,check):actions.addWidget(b)
        layout.addLayout(actions);self.status=QLabel("Chưa có file CSV.");layout.addWidget(self.status);layout.addStretch()
    def choose_folder(self):
        p=QFileDialog.getExistingDirectory(self,"Chọn thư mục lưu CSV",self.folder.text());
        if p:self.folder.setText(p)
    def open_folder(self):Path(self.folder.text()).mkdir(parents=True,exist_ok=True);QDesktopServices.openUrl(QUrl.fromLocalFile(self.folder.text()))
    def check_file(self):
        if self.last_file and Path(self.last_file).exists():QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_file)))
        else:QMessageBox.warning(self,"Kiểm tra CSV","Chưa có file CSV vừa xuất.")
    def set_result(self,result):
        m,c=result.metadata,result.computer;primary=next((x for x in result.network_adapters if x.get("interface_index")==result.primary_adapter_index),{})
        vals={"asset":m.get("asset_code"),"computer":c.get("computer_name"),"serial":c.get("serial_number"),"user":m.get("user"),"department":m.get("department"),"date":m.get("audit_date_display") or m.get("audit_date"),"scan":"Đã hoàn thành kiểm tra máy tính","win11":result.windows11.get("overall"),"windows_license":result.windows_license.get("activation_status"),"office":", ".join(dict.fromkeys(x.get("activation_status","") for x in result.office_licenses)),"mac":primary.get("mac_address"),"ip":", ".join(primary.get("ipv4",[]))}
        for k,l in self.labels.items():l.setText(str(vals.get(k) or "Không có"))
        self.export_btn.setEnabled(True)
    def exported(self,path):self.last_file=path;self.status.setText(f"Đã xuất dữ liệu máy tính thành công.\nTên file: {Path(path).name}\nVị trí: {path}")

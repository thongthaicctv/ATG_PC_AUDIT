from PyQt5.QtWidgets import QDialog,QDialogButtonBox,QFormLayout,QLineEdit,QPlainTextEdit,QTabWidget,QVBoxLayout,QWidget

MANAGED=[("asset_code","Mã tài sản"),("assigned_user","Người sử dụng"),("department","Phòng ban"),("location","Vị trí"),("planned_vlan","VLAN dự kiến"),("planned_ipv4","IP dự kiến"),("planned_gateway","Gateway dự kiến"),("switch_name","Switch"),("switch_port","Cổng switch"),("network_socket","Ổ cắm mạng"),("deployment_status","Trạng thái triển khai"),("note","Ghi chú quản trị")]
class MachineDetailDialog(QDialog):
    def __init__(self,record,parent=None):
        super().__init__(parent);self.record=record;self.setWindowTitle("CHI TIẾT MÁY TÍNH");self.resize(900,650);layout=QVBoxLayout(self);tabs=QTabWidget();manage=QWidget();form=QFormLayout(manage);self.fields={}
        for key,title in MANAGED:field=QLineEdit(str(record.get(key) or ""));form.addRow(title+":",field);self.fields[key]=field
        tabs.addTab(manage,"Hồ sơ & quản lý")
        groups={"Tổng quan":["computer_name","manufacturer","model","serial_number","uuid","os_edition","win11_status"],"Phần cứng":["cpu_name","ram_total_gb","system_disk_model","system_disk_size_gb"],"Mạng và MAC":["primary_adapter_name","primary_mac","current_ipv4","default_gateway","dns_servers"],"Dữ liệu import":list(record.keys())}
        for name,keys in groups.items():page=QPlainTextEdit();page.setReadOnly(True);page.setPlainText("\n".join(f"{k}: {record.get(k,'')}" for k in keys));tabs.addTab(page,name)
        layout.addWidget(tabs);buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
    def updates(self):return {k:v.text().strip() for k,v in self.fields.items()}

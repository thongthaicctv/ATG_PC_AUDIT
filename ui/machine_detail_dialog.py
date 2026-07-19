import json
from PyQt5.QtWidgets import QDialog,QDialogButtonBox,QFormLayout,QHeaderView,QLineEdit,QPlainTextEdit,QTableWidget,QTableWidgetItem,QTabWidget,QVBoxLayout,QWidget

MANAGED=[("asset_code","Loại máy tính"),("assigned_user","Người sử dụng"),("department","Phòng ban"),("location","Vị trí"),("planned_vlan","VLAN dự kiến"),("planned_ipv4","IP dự kiến"),("planned_gateway","Gateway dự kiến"),("switch_name","Switch"),("switch_port","Cổng switch"),("network_socket","Ổ cắm mạng"),("deployment_status","Trạng thái triển khai"),("note","Ghi chú quản trị")]
MANAGED.insert(2,("employee_code","Mã nhân viên"))

class MachineDetailDialog(QDialog):
    def __init__(self,record,usage_history=None,parent=None):
        super().__init__(parent);self.record=record;self.setWindowTitle("CHI TIẾT MÁY TÍNH");self.resize(900,650);layout=QVBoxLayout(self);tabs=QTabWidget();manage=QWidget();form=QFormLayout(manage);self.fields={}
        for key,title in MANAGED:field=QLineEdit(str(record.get(key) or ""));form.addRow(title+":",field);self.fields[key]=field
        tabs.addTab(manage,"Hồ sơ & quản lý")
        history=QTableWidget(0,9);history.setHorizontalHeaderLabels(["Lần","Người sử dụng","Mã NV","Phòng ban","Vị trí","Bắt đầu","Kết thúc","Thay đổi phần cứng / ghi chú","Nguồn"]);history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);history.horizontalHeader().setSectionResizeMode(7,QHeaderView.Stretch)
        rows=usage_history or [{"sequence_no":1,"assigned_user":record.get("assigned_user"),"employee_code":record.get("employee_code"),"department":record.get("department"),"location":record.get("location"),"started_at":record.get("audit_time_iso"),"ended_at":"","note":"Lần sử dụng hiện tại","source":"Tổng hợp"}];history.setRowCount(len(rows))
        for r,item in enumerate(rows):
            for c,key in enumerate(("sequence_no","assigned_user","employee_code","department","location","started_at","ended_at","note","source")):history.setItem(r,c,QTableWidgetItem(str(item.get(key) or ("Hiện tại" if key=="ended_at" else ""))))
        tabs.addTab(history,"Lịch sử sử dụng")
        groups={"Tổng quan":["computer_name","manufacturer","model","serial_number","uuid","os_edition","win11_status"],"Phần cứng":["cpu_name","ram_total_gb","system_disk_model","system_disk_size_gb","gpu_summary"],"Mạng và MAC":["primary_adapter_name","primary_mac","current_ipv4","default_gateway","dns_servers"],"Dữ liệu import":list(record.keys())}
        for name,keys in groups.items():page=QPlainTextEdit();page.setReadOnly(True);page.setPlainText("\n".join(f"{k}: {record.get(k,'')}" for k in keys));tabs.addTab(page,name)
        gpu_page=QPlainTextEdit();gpu_page.setReadOnly(True)
        try:gpus=json.loads(record.get("gpu_details_json") or "[]")
        except Exception:gpus=[]
        if gpus:
            lines=[]
            for index,gpu in enumerate(gpus,1):
                lines.extend([f"Card đồ họa {index}",f"Tên: {gpu.get('name') or 'Không xác định'}",f"Driver: {gpu.get('driver_version') or 'Không xác định'}",f"Bộ nhớ: {gpu.get('adapter_ram_gb') or gpu.get('adapter_ram') or 'Không xác định'} GB",f"Độ phân giải: {gpu.get('resolution') or 'Không xác định'}",f"Trạng thái: {'Đang sử dụng' if gpu.get('is_active') else (gpu.get('status') or 'Đã nhận diện')}",""])
            gpu_page.setPlainText("\n".join(lines).strip())
        else:gpu_page.setPlainText("Chưa có dữ liệu card đồ họa chi tiết. Hãy bấm ĐỒNG BỘ NGAY để tải dữ liệu chi tiết của lần quét.")
        tabs.insertTab(4,gpu_page,"Card đồ họa")
        layout.addWidget(tabs);buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
    def updates(self):return {k:v.text().strip() for k,v in self.fields.items()}

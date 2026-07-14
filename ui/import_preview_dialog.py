from PyQt5.QtWidgets import QDialog,QDialogButtonBox,QTableWidget,QTableWidgetItem,QVBoxLayout

class ImportPreviewDialog(QDialog):
    def __init__(self,previews,parent=None):
        super().__init__(parent);self.setWindowTitle("Xem trước dữ liệu import");self.resize(1100,500);layout=QVBoxLayout(self);headers=["Tên file","Mã tài sản","Tên máy","Serial","Người sử dụng","Phòng ban","Ngày kiểm tra","Schema","Hash","Trạng thái","Hành động","Ghi chú"]
        table=QTableWidget(len(previews),len(headers));table.setHorizontalHeaderLabels(headers)
        for i,p in enumerate(previews):
            r=p.record;vals=[p.file_path,r.get("asset_code"),r.get("computer_name"),r.get("serial_number"),r.get("assigned_user"),r.get("department"),r.get("audit_date_display"),r.get("schema_version"),"Đúng" if p.hash_verified else "Không khớp",p.status,p.action,p.message]
            for j,v in enumerate(vals):table.setItem(i,j,QTableWidgetItem(str(v or "")))
        table.resizeColumnsToContents();layout.addWidget(table);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)

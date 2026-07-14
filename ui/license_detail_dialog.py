from PyQt5.QtWidgets import QDialog,QDialogButtonBox,QFormLayout,QLabel
from core.license_models import mask_device_id


class LicenseDetailDialog(QDialog):
    def __init__(self,result,parent=None):
        super().__init__(parent);self.setWindowTitle("Thông tin license");layout=QFormLayout(self)
        fields=[("Trạng thái",result.status.value),("Đơn vị",result.company or "-"),("Tên license",result.license_name or "-"),("Tính năng","Tổng hợp dữ liệu"),("Ngày hết hạn",result.expire_date or "Vĩnh viễn"),("DEVICE_ID",mask_device_id(result.device_id)),("Nguồn",result.source)]
        for key,value in fields:layout.addRow(key,QLabel(str(value)))
        buttons=QDialogButtonBox(QDialogButtonBox.Close);buttons.rejected.connect(self.reject);layout.addRow(buttons)

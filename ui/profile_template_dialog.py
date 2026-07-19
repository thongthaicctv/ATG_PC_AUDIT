from pathlib import Path

from PyQt5.QtWidgets import QDialog,QFileDialog,QHBoxLayout,QLabel,QMessageBox,QPushButton,QVBoxLayout

from core.profile_template_manager import config_path,export_template,import_template


class ProfileTemplateDialog(QDialog):
    def __init__(self,parent=None,on_updated=None):
        super().__init__(parent);self.on_updated=on_updated;self.setWindowTitle("Cài đặt biểu mẫu danh mục");self.resize(620,210)
        layout=QVBoxLayout(self);info=QLabel(f"Quản lý danh mục dùng chung cho Loại máy tính, Phòng ban và Vị trí làm việc.\n\nXuất biểu mẫu Excel, chỉnh sửa các dòng rồi nhập lại. Danh mục được áp dụng ngay cho các cửa sổ thả xuống.\n\nFile cấu hình đang sử dụng:\n{config_path()}");info.setWordWrap(True);layout.addWidget(info)
        buttons=QHBoxLayout();export=QPushButton("XUẤT BIỂU MẪU EXCEL");load=QPushButton("NHẬP/CẬP NHẬT BIỂU MẪU");close=QPushButton("ĐÓNG");buttons.addWidget(export);buttons.addWidget(load);buttons.addWidget(close);layout.addLayout(buttons)
        export.clicked.connect(self.export_file);load.clicked.connect(self.import_file);close.clicked.connect(self.accept)
    def export_file(self):
        path,_=QFileDialog.getSaveFileName(self,"Xuất biểu mẫu danh mục",str(Path.home()/"Bieu_mau_danh_muc_ATG.xlsx"),"Excel (*.xlsx)")
        if not path:return
        try:result=export_template(path);QMessageBox.information(self,"Xuất biểu mẫu",f"Đã xuất biểu mẫu:\n{result}")
        except Exception as exc:QMessageBox.critical(self,"Không thể xuất biểu mẫu",str(exc))
    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,"Chọn biểu mẫu danh mục",str(Path.home()),"Excel (*.xlsx)")
        if not path:return
        try:
            catalog=import_template(path)
            if self.on_updated:self.on_updated(catalog)
            QMessageBox.information(self,"Cập nhật biểu mẫu",f"Đã cập nhật {len(catalog['machine_types'])} loại máy, {len(catalog['departments'])} phòng ban và {len(catalog['locations'])} vị trí.\nDanh mục đã được áp dụng ngay.")
        except Exception as exc:QMessageBox.critical(self,"Biểu mẫu không hợp lệ",str(exc))

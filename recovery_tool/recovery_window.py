from pathlib import Path
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QCheckBox,QFileDialog,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QMainWindow,QMessageBox,QPushButton,QVBoxLayout,QWidget
from core.storage_path_manager import active_storage
from database.database_manager import DatabaseManager
from recovery_tool.database_locator import locate_databases
from recovery_tool.recovery_service import account_info,reset_password


class RecoveryWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle("ATG PC AUDIT – KHÔI PHỤC ĐĂNG NHẬP");self.setMinimumSize(720,420);root=QWidget();layout=QVBoxLayout(root);form=QFormLayout();self.database=QLineEdit();self.database.setReadOnly(True);self.state=QLabel("Chưa kiểm tra");self.account=QLabel();self.role=QLabel();self.updated=QLabel();form.addRow("Database đang sử dụng:",self.database);form.addRow("Trạng thái database:",self.state);form.addRow("Tên tài khoản:",self.account);form.addRow("Vai trò:",self.role);form.addRow("Cập nhật mật khẩu gần nhất:",self.updated);layout.addLayout(form);row=QHBoxLayout();
        for title,fn in (("TÌM DATABASE TỰ ĐỘNG",self.auto_find),("CHỌN DATABASE",self.choose),("KIỂM TRA DATABASE",self.check),("MỞ THƯ MỤC BACKUP",self.open_backup)):button=QPushButton(title);button.clicked.connect(fn);row.addWidget(button)
        layout.addLayout(row);self.new=QLineEdit();self.confirm=QLineEdit();self.new.setEchoMode(QLineEdit.Password);self.confirm.setEchoMode(QLineEdit.Password);self.must_change=QCheckBox("Buộc đổi mật khẩu sau lần đăng nhập tiếp theo");self.must_change.setChecked(True);password_form=QFormLayout();password_form.addRow("Mật khẩu mới:",self.new);password_form.addRow("Nhập lại mật khẩu:",self.confirm);layout.addLayout(password_form);layout.addWidget(self.must_change);reset=QPushButton("ĐẶT LẠI MẬT KHẨU");reset.clicked.connect(self.reset);layout.addWidget(reset);layout.addWidget(QLabel("Công cụ không thể xem hoặc giải mã mật khẩu cũ. Database sẽ được backup trước khi thay đổi."));self.setCentralWidget(root);self.auto_find()
    def auto_find(self):
        items=locate_databases(Path.cwd())
        if len(items)==1:self.database.setText(str(items[0]));self.check()
        elif len(items)>1:QMessageBox.information(self,"Tìm thấy nhiều database","Tìm thấy nhiều database:\n"+"\n".join(str(x) for x in items)+"\n\nHãy dùng CHỌN DATABASE để xác nhận đúng file.")
        else:self.state.setText("Không tìm thấy database")
    def choose(self):
        path=QFileDialog.getOpenFileName(self,"Chọn database",filter="SQLite (*.db *.sqlite)")[0]
        if path:self.database.setText(path);self.check()
    def check(self):
        result=DatabaseManager().validate_database(self.database.text());self.state.setText("HỢP LỆ – quick_check: ok" if result.valid else "KHÔNG HỢP LỆ – "+result.error_message);info=account_info();self.account.setText(info["username"]);self.role.setText(info["role"]);self.updated.setText(info["updated_at"])
    def open_backup(self):
        root=active_storage().backup_root;root.mkdir(parents=True,exist_ok=True);QDesktopServices.openUrl(QUrl.fromLocalFile(str(root)))
    def reset(self):
        try:
            backup=reset_password(Path(self.database.text()),self.new.text(),self.confirm.text(),self.must_change.isChecked());self.new.clear();self.confirm.clear();QMessageBox.information(self,"Khôi phục đăng nhập",f"Đã đặt mật khẩu mới.\nBackup bắt buộc:\n{backup}");self.check()
        except Exception as exc:QMessageBox.critical(self,"Không thể đặt lại mật khẩu",str(exc))

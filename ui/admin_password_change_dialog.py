from PyQt5.QtWidgets import QCheckBox,QDialog,QDialogButtonBox,QFormLayout,QLineEdit,QMessageBox,QVBoxLayout
from core.admin_auth import change_password

class AdminPasswordChangeDialog(QDialog):
    def __init__(self,parent=None,base_dir=None):
        super().__init__(parent);self.base_dir=base_dir;self.setWindowTitle("Đổi mật khẩu quản trị");layout=QVBoxLayout(self);form=QFormLayout();self.current=QLineEdit();self.new=QLineEdit();self.confirm=QLineEdit()
        for x in (self.current,self.new,self.confirm):x.setEchoMode(QLineEdit.Password)
        form.addRow("Mật khẩu hiện tại:",self.current);form.addRow("Mật khẩu mới:",self.new);form.addRow("Nhập lại:",self.confirm);layout.addLayout(form);show=QCheckBox("Hiển thị mật khẩu");show.toggled.connect(lambda on:[x.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password) for x in (self.current,self.new,self.confirm)]);layout.addWidget(show);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.save);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
    def save(self):
        if self.new.text()!=self.confirm.text():QMessageBox.warning(self,"Mật khẩu","Hai mật khẩu mới không giống nhau.");return
        try:change_password(self.current.text(),self.new.text(),self.base_dir);self.accept()
        except ValueError as e:QMessageBox.warning(self,"Mật khẩu",str(e))

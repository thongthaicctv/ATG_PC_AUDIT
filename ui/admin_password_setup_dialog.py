from PyQt5.QtWidgets import QCheckBox,QDialog,QDialogButtonBox,QFormLayout,QLabel,QLineEdit,QMessageBox,QVBoxLayout
from core.admin_auth import set_password

class AdminPasswordSetupDialog(QDialog):
    def __init__(self,parent=None,base_dir=None):
        super().__init__(parent);self.base_dir=base_dir;self.setWindowTitle("Thiết lập mật khẩu quản trị");layout=QVBoxLayout(self);form=QFormLayout();self.password=QLineEdit();self.confirm=QLineEdit()
        for x in (self.password,self.confirm):x.setEchoMode(QLineEdit.Password)
        form.addRow("Mật khẩu mới:",self.password);form.addRow("Nhập lại:",self.confirm);layout.addLayout(form);self.show=QCheckBox("Hiển thị mật khẩu");self.show.toggled.connect(lambda on:[x.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password) for x in (self.password,self.confirm)]);layout.addWidget(self.show);layout.addWidget(QLabel("Tối thiểu 8 ký tự, có ít nhất một chữ và một số."));buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.save);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
    def save(self):
        if self.password.text()!=self.confirm.text():QMessageBox.warning(self,"Mật khẩu","Hai mật khẩu không giống nhau.");return
        try:set_password(self.password.text(),self.base_dir);self.accept()
        except ValueError as e:QMessageBox.warning(self,"Mật khẩu",str(e))

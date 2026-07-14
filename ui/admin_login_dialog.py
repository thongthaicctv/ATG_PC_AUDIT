from PyQt5.QtWidgets import QCheckBox,QDialog,QFormLayout,QLabel,QLineEdit,QPushButton,QVBoxLayout

class AdminLoginDialog(QDialog):
    def __init__(self,session,base_dir=None,parent=None):
        super().__init__(parent);self.session=session;self.base_dir=base_dir;self.setWindowTitle("Đăng nhập quản trị");layout=QVBoxLayout(self);self.password=QLineEdit();self.password.setEchoMode(QLineEdit.Password);form=QFormLayout();form.addRow("Mật khẩu:",self.password);layout.addLayout(form);show=QCheckBox("Hiển thị mật khẩu");show.toggled.connect(lambda on:self.password.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password));layout.addWidget(show);self.error=QLabel();layout.addWidget(self.error);button=QPushButton("MỞ CHỨC NĂNG TỔNG HỢP");button.clicked.connect(self.login);layout.addWidget(button)
    def login(self):
        ok,msg=self.session.login(self.password.text(),self.base_dir);self.password.clear();self.error.setText(msg)
        if ok:self.accept()

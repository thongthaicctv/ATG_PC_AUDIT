import json,shutil
from pathlib import Path
from PyQt5.QtWidgets import QDialog,QDialogButtonBox,QFileDialog,QFormLayout,QGroupBox,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPushButton,QRadioButton,QVBoxLayout
from core.admin_auth import auth_path,set_password
from core.backup_manager import restore_backup
from core.resource_utils import resource_path
from core.storage_path_manager import StoragePaths,atomic_json_write,detect_legacy_storage,validate_root


class FirstRunStorageDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle("THIẾT LẬP DỮ LIỆU LẦN ĐẦU");self.setMinimumWidth(720);layout=QVBoxLayout(self);layout.addWidget(QLabel("Chọn vị trí lưu dữ liệu bền vững. Ứng dụng sẽ không lưu database trong thư mục EXE hoặc thư mục tạm."));modes=QGroupBox("Bước 1 – Chọn chế độ");ml=QVBoxLayout(modes);self.new=QRadioButton("Tạo dữ liệu mới");self.existing=QRadioButton("Sử dụng database có sẵn");self.restore=QRadioButton("Khôi phục từ file backup");[ml.addWidget(x) for x in (self.new,self.existing,self.restore)];layout.addWidget(modes)
        legacy=detect_legacy_storage(Path(__file__).resolve().parents[1]);self.existing.setChecked(bool(legacy));self.new.setChecked(not legacy);form=QFormLayout();defaults=StoragePaths.defaults();self.data_root=QLineEdit(str(defaults.data_root));self.backup_root=QLineEdit(str(defaults.backup_root));self.database_file=QLineEdit(str(legacy[0]) if legacy else str(defaults.database_path));self.backup_file=QLineEdit();self.username=QLineEdit("administrator");self.display_name=QLineEdit("Quản trị viên");self.password=QLineEdit();self.confirm=QLineEdit();self.password.setEchoMode(QLineEdit.Password);self.confirm.setEchoMode(QLineEdit.Password)
        form.addRow("Thư mục dữ liệu:",self._picker(self.data_root,True));form.addRow("Thư mục backup:",self._picker(self.backup_root,True));self.database_label=QLabel();form.addRow(self.database_label,self._database_picker());form.addRow("File backup:",self._picker(self.backup_file,False,"ATG Backup (*.atgbackup)"));form.addRow("Tên đăng nhập:",self.username);form.addRow("Tên quản trị:",self.display_name);form.addRow("Mật khẩu mới:",self.password);form.addRow("Nhập lại:",self.confirm);layout.addLayout(form);layout.addWidget(QLabel("Nếu sử dụng database hiện có và mật khẩu quản trị đã tồn tại, có thể để trống hai ô mật khẩu."));buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.button(QDialogButtonBox.Ok).setText("HOÀN TẤT THIẾT LẬP");buttons.accepted.connect(self.finish);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
        self.data_root.textChanged.connect(self._data_root_changed)
        for mode in (self.new,self.existing,self.restore):mode.toggled.connect(self._mode_changed)
        self._mode_changed()
    def _picker(self,field,directory,filter_text=""):
        box=QHBoxLayout();box.addWidget(field);button=QPushButton("Chọn...");button.clicked.connect(lambda:self._choose(field,directory,filter_text));box.addWidget(button);return box
    def _choose(self,field,directory,filter_text):
        value=QFileDialog.getExistingDirectory(self,"Chọn thư mục",field.text()) if directory else QFileDialog.getOpenFileName(self,"Chọn file",field.text(),filter=filter_text)[0]
        if value:field.setText(value)
    def _database_picker(self):
        box=QHBoxLayout();box.addWidget(self.database_file);button=QPushButton("Chọn...");button.clicked.connect(self._choose_database);box.addWidget(button);return box
    def _default_database_path(self):
        text=self.data_root.text().strip()
        return str(Path(text)/"database"/"atg_pc_audit_master.db") if text else ""
    def _data_root_changed(self):
        if self.new.isChecked() or self.restore.isChecked():self.database_file.setText(self._default_database_path())
    def _mode_changed(self):
        if self.existing.isChecked():self.database_label.setText("Database có sẵn:")
        else:
            self.database_label.setText("Lưu database tại:")
            self.database_file.setText(self._default_database_path())
    def _choose_database(self):
        if self.existing.isChecked():value=QFileDialog.getOpenFileName(self,"Chọn database có sẵn",self.database_file.text(),"Database (*.db *.sqlite)")[0]
        else:
            value=QFileDialog.getSaveFileName(self,"Chọn vị trí lưu database",self.database_file.text(),"Database (*.db)")[0]
            if value and not Path(value).suffix:value += ".db"
        if value:self.database_file.setText(value)
    def finish(self):
        try:
            root=Path(self.data_root.text().strip());backup=Path(self.backup_root.text().strip());warnings=validate_root(root)+validate_root(backup,True)
            if warnings and QMessageBox.warning(self,"Cảnh báo đường dẫn","\n".join(warnings)+"\n\nBạn vẫn muốn tiếp tục?",QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
            paths=StoragePaths.defaults();paths.data_root=root;paths.database_path=Path(self.database_file.text().strip());paths.config_path=root/"config"/"app_config.json";paths.logs_path=root/"logs";paths.exports_path=root/"exports";paths.backup_root=backup
            if not self.database_file.text().strip():raise ValueError("Chưa chọn đường dẫn database.")
            paths.ensure_directories()
            bundled=resource_path("config/app_config.json")
            if bundled.exists() and bundled.resolve()!=paths.config_path.resolve():atomic_json_write(paths.config_path,json.loads(bundled.read_text(encoding="utf-8")))
            if self.existing.isChecked():
                source=Path(self.database_file.text().strip())
                if not source.is_file():raise ValueError("Chưa chọn database có sẵn.")
            elif self.restore.isChecked():
                source=Path(self.backup_file.text().strip())
                if not source.is_file():raise ValueError("Chưa chọn file backup.")
                restore_backup(source,paths.database_path,paths.config_path,paths,auth_path())
            else:
                from core.aggregate_database import AggregateDatabase
                AggregateDatabase(paths.database_path)
            paths.save()
            if self.password.text() or not auth_path().exists():
                if self.password.text()!=self.confirm.text():raise ValueError("Mật khẩu nhập lại không khớp.")
                set_password(self.password.text());data=json.loads(auth_path().read_text(encoding="utf-8"));data["username"]=self.username.text().strip() or "administrator";data["display_name"]=self.display_name.text().strip() or "Quản trị viên";atomic_json_write(auth_path(),data)
            self.accept()
        except Exception as exc:QMessageBox.critical(self,"Không thể thiết lập dữ liệu",str(exc))

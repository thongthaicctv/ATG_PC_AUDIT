import json
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QApplication,QFileDialog,QGridLayout,QGroupBox,QLabel,QMessageBox,QPushButton,QVBoxLayout
from core.backup_manager import create_backup,get_latest_valid_backup,restore_backup,validate_backup
from core.storage_path_manager import StoragePaths,active_storage,atomic_json_write,validate_root
from database.database_manager import DatabaseManager


class DataManagementWidget(QGroupBox):
    def __init__(self,on_database_changed=None,parent=None):
        super().__init__("QUẢN LÝ DỮ LIỆU VÀ SAO LƯU",parent);self.on_database_changed=on_database_changed;layout=QVBoxLayout(self);self.info=QLabel();self.info.setWordWrap(True);layout.addWidget(self.info);buttons=QGridLayout();actions=(("MỞ THƯ MỤC DATABASE",self.open_database),("MỞ THƯ MỤC CONFIG",self.open_config),("THAY ĐỔI THƯ MỤC DỮ LIỆU",self.change_data_root),("CHỌN THƯ MỤC BACKUP",self.choose_backup),("SAO LƯU NGAY",self.backup_now),("KHÔI PHỤC DỮ LIỆU",self.restore_now),("KIỂM TRA DATABASE",self.validate_database),("SAO CHÉP THÔNG TIN ĐƯỜNG DẪN",self.copy_paths))
        for i,(title,fn) in enumerate(actions):button=QPushButton(title);button.clicked.connect(fn);buttons.addWidget(button,i//4,i%4)
        layout.addLayout(buttons);self.refresh()
    def refresh(self):
        p=active_storage();db=p.database_path;latest=get_latest_valid_backup(p.backup_root) if p.backup_root.exists() else None;size=f"{db.stat().st_size/1024/1024:.2f} MB" if db.exists() else "Không tồn tại";updated=datetime.fromtimestamp(db.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S") if db.exists() else "Không có";self.info.setText(f"Database: {db}\nDung lượng: {size} | Cập nhật: {updated}\nConfig: {p.config_path}\nLog: {p.logs_path}\nXuất báo cáo: {p.exports_path}\nBackup: {p.backup_root}\nBackup gần nhất: {latest or 'Chưa có'}")
    @staticmethod
    def _open(path):Path(path).mkdir(parents=True,exist_ok=True);QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    def open_database(self):self._open(active_storage().database_path.parent)
    def open_config(self):self._open(active_storage().config_path.parent)
    def choose_backup(self):
        folder=QFileDialog.getExistingDirectory(self,"Chọn thư mục backup",str(active_storage().backup_root))
        if not folder:return
        try:validate_root(folder,True);paths=active_storage();paths.backup_root=Path(folder);paths.save();self.refresh()
        except Exception as exc:QMessageBox.critical(self,"Đường dẫn backup",str(exc))
    def backup_now(self):
        p=active_storage();result=create_backup(p.database_path,p.backup_root,p.config_path,p.bootstrap_path)
        if result.success:QMessageBox.information(self,"Sao lưu",f"Sao lưu và kiểm tra thành công:\n{result.backup_path}");self.refresh()
        else:QMessageBox.critical(self,"Sao lưu không hoàn thành",result.error_message)
    def restore_now(self):
        path=QFileDialog.getOpenFileName(self,"Chọn backup",str(active_storage().backup_root),"ATG Backup (*.atgbackup)")[0]
        if not path:return
        check=validate_backup(path)
        if not check.success:QMessageBox.critical(self,"Backup không hợp lệ",check.error_message);return
        if QMessageBox.question(self,"Khôi phục","Database hiện tại sẽ được backup an toàn trước khi khôi phục. Tiếp tục?")!=QMessageBox.Yes:return
        try:
            p=active_storage();restore_backup(path,p.database_path,p.config_path,p);QMessageBox.information(self,"Khôi phục","Khôi phục thành công.");self.refresh()
            if self.on_database_changed:self.on_database_changed(p.database_path)
        except Exception as exc:QMessageBox.critical(self,"Khôi phục thất bại",str(exc))
    def validate_database(self):
        result=DatabaseManager().validate_database(active_storage().database_path);QMessageBox.information(self,"Kiểm tra database",f"Quick check: {result.quick_check}\nBảng: {len(result.tables)}\nBản ghi: {result.record_counts}" if result.valid else result.error_message)
    def copy_paths(self):
        p=active_storage();QApplication.clipboard().setText(f"Bootstrap: {p.bootstrap_path}\nDatabase: {p.database_path}\nConfig: {p.config_path}\nLogs: {p.logs_path}\nExports: {p.exports_path}\nBackups: {p.backup_root}");QMessageBox.information(self,"Đường dẫn","Đã sao chép thông tin đường dẫn.")
    def change_data_root(self):
        folder=QFileDialog.getExistingDirectory(self,"Chọn thư mục dữ liệu mới",str(active_storage().data_root))
        if not folder:return
        try:
            warnings=validate_root(folder)
            if warnings and QMessageBox.warning(self,"Cảnh báo SQLite","\n".join(warnings)+"\n\nBạn vẫn muốn tiếp tục?",QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
            old=active_storage();root=Path(folder);new=StoragePaths(old.bootstrap_path,root,root/"database"/old.database_path.name,root/"config"/"app_config.json",root/"logs",root/"exports",old.backup_root);new.ensure_directories();safety=create_backup(old.database_path,old.backup_root,old.config_path,old.bootstrap_path,prefix="BEFORE_STORAGE_MIGRATION")
            if not safety.success:raise ValueError("Không thể backup trước khi chuyển: "+safety.error_message)
            DatabaseManager(old.database_path).create_consistent_backup(new.database_path);atomic_json_write(new.config_path,json.loads(old.config_path.read_text(encoding="utf-8")));new.save();migrated=old.database_path.with_suffix(f".migrated_{datetime.now():%Y%m%d_%H%M%S}.db");old.database_path.rename(migrated);QMessageBox.information(self,"Chuyển dữ liệu",f"Đã chuyển dữ liệu. Database cũ giữ tại:\n{migrated}");self.refresh()
            if self.on_database_changed:self.on_database_changed(new.database_path)
        except Exception as exc:QMessageBox.critical(self,"Không thể chuyển dữ liệu",str(exc))

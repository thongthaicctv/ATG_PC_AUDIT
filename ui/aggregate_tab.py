from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import QAbstractTableModel,QModelIndex,Qt,QTimer
from PyQt5.QtWidgets import QApplication,QCheckBox,QFileDialog,QGridLayout,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QProgressBar,QPushButton,QStackedWidget,QTableView,QVBoxLayout,QWidget

from core.admin_auth import AdminSession,auth_path
from core.aggregate_database import AggregateDatabase
from core.backup_manager import backup_database,restore_database
from core.csv_importer import import_previews,preview_files
from core.excel_report_exporter import export_company_report
from core.report_worker import TaskWorker
from core.device_id import collect_device_identity
from core.license_client import LicenseClient,require_feature_license,LicenseRequiredError
from core.license_models import mask_device_id
from ui.admin_login_dialog import AdminLoginDialog
from ui.admin_password_change_dialog import AdminPasswordChangeDialog
from ui.admin_password_setup_dialog import AdminPasswordSetupDialog
from ui.import_preview_dialog import ImportPreviewDialog
from ui.machine_detail_dialog import MachineDetailDialog
from ui.license_activation_dialog import LicenseActivationDialog
from ui.license_detail_dialog import LicenseDetailDialog
from workers.license_check_worker import LicenseCheckWorker

DISPLAY=[("asset_code","Mã tài sản"),("computer_name","Tên máy"),("assigned_user","Người sử dụng"),("department","Phòng ban"),("location","Vị trí"),("manufacturer","Hãng"),("model","Model"),("serial_number","Serial"),("cpu_name","CPU"),("ram_total_gb","RAM"),("system_disk_media_type","Ổ hệ thống"),("system_disk_size_gb","Dung lượng"),("os_edition","Windows"),("windows_activation_status","Windows Activation"),("office_product_summary","Office"),("office_activation_summary","Office Activation"),("tpm_version","TPM"),("secure_boot_status","Secure Boot"),("win11_status","Windows 11"),("primary_mac","MAC chính"),("current_ipv4","IP hiện tại"),("planned_vlan","VLAN"),("planned_ipv4","IP dự kiến"),("switch_name","Switch"),("switch_port","Cổng"),("audit_date_display","Ngày kiểm tra"),("auditor","Người kiểm tra"),("recommendations","Khuyến nghị")]

class RecordsModel(QAbstractTableModel):
    def __init__(self):super().__init__();self.rows=[]
    def set_rows(self,rows):self.beginResetModel();self.rows=rows;self.endResetModel()
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.rows)
    def columnCount(self,parent=QModelIndex()):return len(DISPLAY)+1
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid():return None
        if role in (Qt.DisplayRole,Qt.EditRole):return index.row()+1 if index.column()==0 else str(self.rows[index.row()].get(DISPLAY[index.column()-1][0],"") or "")
    def headerData(self,section,orientation,role=Qt.DisplayRole):
        if role!=Qt.DisplayRole:return None
        return ("STT" if section==0 else DISPLAY[section-1][1]) if orientation==Qt.Horizontal else section+1

class AggregateTab(QWidget):
    def __init__(self):
        super().__init__();self.session=AdminSession();self.db=None;self.selected_paths=[];self.previews=[];self.worker=None;self.license_worker=None;self.license_checking=False;self.license_result=None;self.license_client=LicenseClient();root=QVBoxLayout(self);self.stack=QStackedWidget();root.addWidget(self.stack)
        try:self.identity=collect_device_identity()
        except Exception as exc:self.identity=type("Identity",(),{"device_id":"KHÔNG-TẠO-ĐƯỢC","confidence":"LOW","is_fallback":True})();self.identity_error=str(exc)
        self.lock_page=QWidget();ll=QVBoxLayout(self.lock_page);title=QLabel("TỔNG HỢP DỮ LIỆU TOÀN CÔNG TY");title.setStyleSheet("font-size:20px;font-weight:bold");ll.addWidget(title)
        self.license_state=QLabel("Trạng thái license: Chưa kiểm tra");self.license_state.setWordWrap(True);ll.addWidget(self.license_state);ll.addWidget(QLabel("DEVICE_ID: "+mask_device_id(self.identity.device_id)))
        license_buttons=QHBoxLayout();activate=QPushButton("KÍCH HOẠT / KIỂM TRA LICENSE");activate.clicked.connect(self.activate_license);copy=QPushButton("SAO CHÉP DEVICE ID");copy.clicked.connect(lambda:QApplication.clipboard().setText(self.identity.device_id));details=QPushButton("XEM THÔNG TIN LICENSE");details.clicked.connect(self.show_license_detail)
        for b in (activate,copy,details):license_buttons.addWidget(b)
        ll.addLayout(license_buttons);ll.addWidget(QLabel("Sau khi license hợp lệ, hãy xác thực lớp mật khẩu quản trị."));self.password=QLineEdit();self.password.setEchoMode(QLineEdit.Password);self.password.setPlaceholderText("Nhập mật khẩu quản trị");self.password.setEnabled(False);ll.addWidget(self.password);show=QCheckBox("Hiển thị mật khẩu");show.toggled.connect(lambda on:self.password.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password));ll.addWidget(show);self.login_error=QLabel();ll.addWidget(self.login_error);self.login_btn=QPushButton("MỞ CHỨC NĂNG TỔNG HỢP");self.login_btn.clicked.connect(self.login);self.login_btn.setEnabled(False);ll.addWidget(self.login_btn);self.setup_btn=QPushButton("THIẾT LẬP MẬT KHẨU LẦN ĐẦU");self.setup_btn.clicked.connect(self.setup_password);self.setup_btn.setEnabled(False);ll.addWidget(self.setup_btn);ll.addStretch();self.stack.addWidget(self.lock_page)
        self.admin_page=QWidget();al=QVBoxLayout(self.admin_page);tools=QGridLayout();actions=[("IMPORT FILE CSV",self.pick_one),("IMPORT NHIỀU FILE",self.pick_many),("IMPORT CẢ THƯ MỤC",self.pick_folder),("XEM TRƯỚC",self.preview),("XÁC NHẬN IMPORT",self.confirm_import),("XÓA DÒNG ĐANG CHỌN",self.delete_selected),("XUẤT BÁO CÁO EXCEL",self.export_excel),("SAO LƯU DỮ LIỆU",self.backup),("KHÔI PHỤC DỮ LIỆU",self.restore),("ĐỔI MẬT KHẨU",self.change_password),("KHÓA LẠI",self.lock)]
        for i,(t,fn) in enumerate(actions):b=QPushButton(t);b.clicked.connect(fn);tools.addWidget(b,i//6,i%6)
        al.addLayout(tools);self.stats=QLabel();self.stats.setWordWrap(True);self.stats.setStyleSheet("background:#eaf2f8;padding:8px;font-weight:bold");al.addWidget(self.stats);filters=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText("Tìm kiếm chung");self.department=QLineEdit();self.department.setPlaceholderText("Phòng ban");self.user=QLineEdit();self.user.setPlaceholderText("Người sử dụng");apply=QPushButton("ÁP DỤNG BỘ LỌC");apply.clicked.connect(self.refresh);clear=QPushButton("XÓA BỘ LỌC");clear.clicked.connect(self.clear_filters)
        for x in (self.search,self.department,self.user,apply,clear): filters.addWidget(x)
        al.addLayout(filters);self.model=RecordsModel();self.table=QTableView();self.table.setModel(self.model);self.table.setSortingEnabled(True);self.table.setSelectionBehavior(QTableView.SelectRows);self.table.doubleClicked.connect(self.detail);al.addWidget(self.table,1);self.progress=QProgressBar();self.progress.setVisible(False);al.addWidget(self.progress);self.task_status=QLabel();al.addWidget(self.task_status);self.stack.addWidget(self.admin_page)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(1000);self.update_lock_ui();QTimer.singleShot(0,self.check_license_silently)
    def on_open(self):
        if self.license_checking:return
        if not self.license_result:self.check_license_silently()
    def check_license_silently(self):
        if self.license_checking or self.identity.device_id=="KHÔNG-TẠO-ĐƯỢC":return
        self.license_checking=True;self.license_state.setText("Trạng thái license: Đang kiểm tra tự động...")
        self.license_worker=LicenseCheckWorker(self.license_client,self.identity.device_id,self)
        self.license_worker.completed.connect(self._silent_license_completed)
        self.license_worker.failed.connect(self._silent_license_failed)
        self.license_worker.finished.connect(self._silent_license_finished)
        self.license_worker.start()
    def _silent_license_completed(self,result):
        self.license_result=result;self.update_lock_ui()
    def _silent_license_failed(self,message):
        self.license_state.setText("Trạng thái license: Không thể kiểm tra - "+message)
    def _silent_license_finished(self):
        self.license_checking=False;self.license_worker=None
    def activate_license(self):
        dialog=LicenseActivationDialog(self.identity,self.license_client,self.license_result,self)
        if dialog.exec_()==dialog.Accepted and dialog.result and dialog.result.is_valid:self.license_result=dialog.result;self.update_lock_ui()
        elif dialog.result:self.license_result=dialog.result;self.update_lock_ui()
    def show_license_detail(self):
        if self.license_result:LicenseDetailDialog(self.license_result,self).exec_()
        else:self.activate_license()
    def update_lock_ui(self):
        exists=auth_path().exists();valid=bool(self.license_result and self.license_result.is_valid);self.setup_btn.setVisible(not exists);self.setup_btn.setEnabled(valid);self.password.setEnabled(valid);self.login_btn.setEnabled(valid and exists and not self.session.remaining_lock());self.login_error.setText(("" if exists else "Chưa thiết lập mật khẩu quản trị.") if valid else "Cần license hợp lệ trước khi xác thực mật khẩu.")
        if self.license_result:
            source=" (update)" if self.license_result.source=="ONLINE" else " (ngoại tuyến)" if self.license_result.source=="OFFLINE_CACHE" else ""
            self.license_state.setText("Trạng thái license: "+self.license_result.message+source)
    def setup_password(self):
        if AdminPasswordSetupDialog(self).exec_():self.update_lock_ui()
    def login(self):
        try:require_feature_license(self.license_result)
        except LicenseRequiredError:self.activate_license();return
        ok,msg=self.session.login(self.password.text());self.password.clear();self.login_error.setText(msg)
        if ok:self.db=AggregateDatabase();self.stack.setCurrentWidget(self.admin_page);self.refresh()
    def tick(self):
        if self.stack.currentWidget()==self.admin_page and not self.session.is_active():self.lock()
        elif self.session.remaining_lock():self.login_btn.setEnabled(False);self.login_error.setText(f"Đang khóa. Còn {self.session.remaining_lock()} giây.")
        elif auth_path().exists() and self.license_result and self.license_result.is_valid:self.login_btn.setEnabled(True)
    def lock(self):self.session.lock();self.stack.setCurrentWidget(self.lock_page);self.update_lock_ui()
    def touch(self):self.session.touch()
    def pick_one(self):
        p,_=QFileDialog.getOpenFileName(self,"Chọn CSV",filter="CSV (*.csv)");self.selected_paths=[Path(p)] if p else []
    def pick_many(self):
        ps,_=QFileDialog.getOpenFileNames(self,"Chọn nhiều CSV",filter="CSV (*.csv)");self.selected_paths=[Path(x) for x in ps]
    def pick_folder(self):
        p=QFileDialog.getExistingDirectory(self,"Chọn thư mục CSV");self.selected_paths=[Path(p)] if p else []
    def _task(self,fn,done,*args):
        try:require_feature_license(self.license_result)
        except LicenseRequiredError:self.activate_license();return
        self.progress.setVisible(True);self.worker=TaskWorker(fn,*args,parent=self);self.worker.progress.connect(lambda p,s:(self.progress.setValue(p),self.task_status.setText(s)));self.worker.completed.connect(lambda r:(self.progress.setVisible(False),done(r)));self.worker.failed.connect(lambda e:(self.progress.setVisible(False),QMessageBox.critical(self,"Lỗi",e)));self.worker.start()
    def preview(self):
        if not self.selected_paths:QMessageBox.warning(self,"Import","Chưa chọn file hoặc thư mục CSV.");return
        self._task(preview_files,self.preview_done,self.selected_paths,self.db)
    def preview_done(self,items):self.previews=items;ImportPreviewDialog(items,self).exec_();self.touch()
    def confirm_import(self):
        if not self.previews:QMessageBox.warning(self,"Import","Hãy xem trước dữ liệu trước khi import.");return
        limit=self.license_result.max_import_records if self.license_result else 0
        if limit and self.db.stats()["total_machines"]+sum(1 for x in self.previews if getattr(x,"action","import")!="skip")>limit:QMessageBox.warning(self,"Giới hạn license",f"License hiện tại cho phép quản lý tối đa {limit} máy.");return
        self._task(import_previews,self.import_done,self.previews,self.db)
    def import_done(self,count):QMessageBox.information(self,"Import",f"Đã import {count} bản ghi.");self.previews=[];self.refresh();self.touch()
    def refresh(self):
        if not self.db:return
        rows=self.db.current_records(self.search.text(),self.department.text(),self.user.text());self.model.set_rows(rows);s=self.db.stats();self.stats.setText(f"Tổng máy: {s['total_machines']} | Người dùng: {s['users']} | Phòng ban: {s['departments']} | Win11 đạt/không/cần kiểm tra: {s['win11_pass']}/{s['win11_fail']}/{s['win11_unknown']} | Windows chưa kích hoạt: {s['windows_unlicensed']} | Office chưa kích hoạt: {s['office_unlicensed']} | RAM<8GB: {s['low_ram']} | HDD: {s['hdd']}");self.table.resizeColumnsToContents();self.touch()
    def clear_filters(self):self.search.clear();self.department.clear();self.user.clear();self.refresh()
    def detail(self,index):
        if 0<=index.row()<len(self.model.rows):
            record=self.model.rows[index.row()];dialog=MachineDetailDialog(record,self)
            if dialog.exec_()==dialog.Accepted:self.db.update_management(record["machine_id"],record["audit_row_id"],dialog.updates());self.refresh()
            self.touch()
    def delete_selected(self):
        row=self.table.currentIndex().row()
        if row<0:return
        machine_id=self.model.rows[row]["machine_id"]
        if QMessageBox.question(self,"Xóa","Đánh dấu máy này không còn hoạt động?")==QMessageBox.Yes:
            with self.db.connect() as con:con.execute("UPDATE machines SET is_active=0 WHERE id=?",(machine_id,))
            self.refresh()
    def export_excel(self):
        path,_=QFileDialog.getSaveFileName(self,"Xuất báo cáo",f"BAO_CAO_MAY_TINH_TOAN_CONG_TY_{datetime.now():%Y%m%d_%H%M%S}.xlsx","Excel (*.xlsx)")
        if path:self._task(export_company_report,lambda p:QMessageBox.information(self,"Excel",f"Đã xuất:\n{p}"),self.db,Path(path),"Quản trị viên",self.license_result)
    def backup(self):
        folder=QFileDialog.getExistingDirectory(self,"Chọn thư mục backup")
        if folder:self._task(backup_database,lambda p:QMessageBox.information(self,"Backup",f"Đã sao lưu:\n{p}"),self.db.path,Path(folder))
    def restore(self):
        if AdminLoginDialog(self.session,parent=self).exec_()!=AdminLoginDialog.Accepted:return
        path,_=QFileDialog.getOpenFileName(self,"Chọn backup",filter="ZIP (*.zip)")
        if path:self._task(restore_database,lambda p:(QMessageBox.information(self,"Khôi phục","Khôi phục thành công."),self.refresh()),Path(path),self.db.path)
    def change_password(self):AdminPasswordChangeDialog(self).exec_();self.touch()

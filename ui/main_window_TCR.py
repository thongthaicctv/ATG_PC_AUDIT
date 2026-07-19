from PyQt5.QtCore import QDate, QUrl, Qt, QTimer
from PyQt5.QtGui import QDesktopServices, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QDateEdit, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QComboBox, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QFileDialog, QScrollArea, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from core.admin_utils import is_admin, restart_as_admin
from core.audit_worker import AuditWorker
from ui.aggregate_tab import AggregateTab
from ui.export_tab import ExportTab
from ui.hardware_tab import HardwareTab
from ui.license_tab import LicenseTab
from ui.network_tab import NetworkTab
from ui.overview_tab import OverviewTab
from ui.windows_tab import WindowsTab
from core.sync_service import SyncService,sync_config
from workers.submit_audit_worker import SubmitAuditWorker
from workers.retry_queue_worker import RetryQueueWorker
from core.export_manager import export_license_csv, export_machine_excel, export_network_csv, save_complete_record, save_json
from core.csv_exporter import export_csv as export_admin_csv
from core.resource_utils import resource_path
from core.profile_validator import REQUIRED_FIELDS,normalize_employee_code,validate_required_profile_fields
from core.profile_template_manager import load_catalog
from ui.profile_template_dialog import ProfileTemplateDialog
import json
from pathlib import Path
from core.storage_path_manager import atomic_json_write


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.sync_worker = None
        self.retry_worker = None
        try:self.sync_service=SyncService()
        except Exception:self.sync_service=None
        self.last_result = None
        self.setWindowTitle("TCR PC CHECK – Kiểm tra máy tính và quy hoạch IP") # đổi tên đơn vị sử dụng
        self.setWindowIcon(QIcon(str(resource_path("assets/app.ico"))))
        self.setMinimumSize(960, 640)
        self.resize(1200, 720)
        self._build_ui()
        self._show_admin_state()
        if self.sync_service and sync_config().get("retry_queue_on_startup",True):QTimer.singleShot(3000,self.retry_due_data)

    def _build_ui(self):
        root = QWidget()
        root.setMinimumWidth(1000)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        brand = QHBoxLayout()
        logo = QLabel()
        logo.setFixedSize(54, 54)
        logo.setPixmap(QPixmap(str(resource_path("assets/logo.png"))).scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand_text = QVBoxLayout()
        brand_title = QLabel("TCR PC CHECK") # đổi tên đơn vị sử dụng
        brand_title.setStyleSheet("font-size:20px;font-weight:700;color:#12376b")
        brand_subtitle = QLabel("Kiểm tra máy tính • Quy hoạch IP • Tổng hợp tài sản CNTT • Hỗ trợ trực tiếp Zalo 0904143113") # đổi tên đơn vị sử dụng
        brand_subtitle.setStyleSheet("color:#d00000; font-size:12px; font-weight:700;")
        brand_text.addWidget(brand_title); brand_text.addWidget(brand_subtitle)
        brand.addWidget(logo); brand.addLayout(brand_text); brand.addStretch()
        layout.addLayout(brand)
        self.admin_banner = QLabel()
        self.admin_banner.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.admin_banner)

        box = QGroupBox("Thông tin hồ sơ")
        grid = QGridLayout(box)
        self.fields = {name: QLineEdit() for name in ["asset_code", "user", "employee_code", "department", "location", "auditor"]}
        for key in ("asset_code","department","location"):self.fields[key]=QComboBox()
        self._apply_profile_catalog(load_catalog())
        profile_hints = {
            "asset_code": "Chọn một trong ba loại máy tính",
            "user": "Ví dụ: Bùi Duy Thông",
            "employee_code": "Ví dụ: NV001 hoặc HCNS-001",
            "department": "Ví dụ: HCNS, Kế toán, Kỹ thuật",
            "location": "Ví dụ: Tầng 2 - Phòng HCNS",
            "auditor": "Ví dụ: Nguyễn Văn A",
        }
        for field in self.fields.values():
            field.setMinimumHeight(30)
            field.setMinimumWidth(180)
        for key, hint in profile_hints.items():
            if isinstance(self.fields[key], QLineEdit): self.fields[key].setPlaceholderText(hint)
            self.fields[key].setToolTip(hint)
        self.fields["employee_code"].setToolTip("Mã định danh duy nhất của nhân viên trong công ty. Dùng để phân biệt những nhân viên có cùng họ tên.")
        self.fields["employee_code"].editingFinished.connect(self._normalize_employee_code)
        for key,_ in REQUIRED_FIELDS:
            signal = self.fields[key].currentTextChanged if isinstance(self.fields[key], QComboBox) else self.fields[key].textChanged
            signal.connect(lambda _text,k=key:self._clear_field_error(k))
        self.notes = QTextEdit(); self.notes.setMaximumHeight(55)
        self.notes.setMinimumHeight(48)
        self.notes.setPlaceholderText("Nhập ghi chú nhanh, ví dụ: Máy cần sao lưu dữ liệu trước khi cài lại Windows...")
        self.notes.setToolTip("Ghi chú tình trạng máy hoặc yêu cầu cần xử lý trước khi cài đặt.")
        self.audit_date = QDateEdit(); self.audit_date.setDisplayFormat("dd/MM/yyyy"); self.audit_date.setCalendarPopup(True); self.audit_date.setDate(QDate.currentDate()); self.audit_date.setMinimumHeight(30)
        self.audit_date.setToolTip("Chọn ngày thực hiện kiểm tra máy tính.")
        top=[("Loại máy tính","asset_code"),("Người sử dụng","user"),("Mã nhân viên","employee_code"),("Phòng ban","department")]
        for col,(title,key) in enumerate(top):grid.addWidget(QLabel(f'{title} <span style="color:#d00000;">*</span>'),0,col);grid.addWidget(self.fields[key],1,col)
        second=[("Vị trí làm việc","location",0,2),("Người thực hiện cập nhật","auditor",2,1)]
        for title,key,col,span in second:grid.addWidget(QLabel(f'{title} <span style="color:#d00000;">*</span>'),2,col,1,span);grid.addWidget(self.fields[key],3,col,1,span)
        grid.addWidget(QLabel("Ngày kiểm tra"),2,3)
        date_tools=QHBoxLayout();date_tools.setContentsMargins(0,0,0,0);date_tools.addWidget(self.audit_date,1)
        self.template_button=QPushButton("CÀI ĐẶT BIỂU MẪU");self.template_button.setToolTip("Xuất hoặc nhập danh mục Loại máy tính, Phòng ban và Vị trí làm việc");self.template_button.clicked.connect(self.open_profile_template_settings);date_tools.addWidget(self.template_button)
        grid.addLayout(date_tools,3,3)
        grid.addWidget(QLabel("Ghi chú"),4,0);grid.addWidget(self.notes,5,0,1,4)
        grid.setColumnStretch(0,28);grid.setColumnStretch(1,26);grid.setColumnStretch(2,16);grid.setColumnStretch(3,30)
        layout.addWidget(box)

        buttons = QHBoxLayout()
        self.scan_button = QPushButton("QUÉT MÁY TÍNH")
        self.rescan_button = QPushButton("QUÉT LẠI")
        self.admin_button = QPushButton("KHỞI ĐỘNG LẠI VỚI QUYỀN QUẢN TRỊ")
        self.scan_button.clicked.connect(self.start_scan)
        self.rescan_button.clicked.connect(self.start_scan)
        self.admin_button.clicked.connect(self.elevate)
        for button in (self.scan_button, self.rescan_button, self.admin_button): buttons.addWidget(button)
        layout.addLayout(buttons)
        self.progress = QProgressBar(); self.status = QLabel("Sẵn sàng")
        self.progress.setVisible(False)
        layout.addWidget(self.progress); layout.addWidget(self.status)
        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(500)
        self.overview_tab, self.hardware_tab, self.windows_tab = OverviewTab(), HardwareTab(), WindowsTab()
        self.tabs.addTab(self.overview_tab, "Tổng quan")
        self.tabs.addTab(self.hardware_tab, "Phần cứng")
        self.tabs.addTab(self.windows_tab, "Windows")
        self.network_tab = NetworkTab()
        self.tabs.addTab(self.network_tab, "Mạng & IP")
        self.license_tab = LicenseTab()
        self.tabs.addTab(self.license_tab, "Bản quyền")
        self.export_tab = ExportTab(); self.aggregate_tab = AggregateTab()
        self.export_tab.export_requested.connect(self.export_management_csv); self.export_tab.send_requested.connect(self.send_management_data);self.export_tab.retry_requested.connect(self.retry_pending_data); self.export_tab.auto_changed.connect(self.save_auto_export_setting)
        try:
            cfg=sync_config();self.export_tab.auto.setChecked(bool(cfg.get("auto_submit_after_scan",False)))
        except Exception: pass
        self.tabs.addTab(self.export_tab, "Xuất dữ liệu")
        self.tabs.addTab(self.aggregate_tab, "Tổng hợp")
        self.tabs.currentChanged.connect(lambda index: self.aggregate_tab.on_open() if self.tabs.widget(index) is self.aggregate_tab else None)
        layout.addWidget(self.tabs, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)
        self.setStyleSheet("QMainWindow{background:#f4f6f8} QGroupBox{font-weight:bold;margin-top:8px;padding-top:8px} QLineEdit,QDateEdit,QComboBox{min-height:28px;padding:2px 6px} QLineEdit[readOnly='false']{background:white} QPushButton{min-height:28px;padding:5px 10px;font-weight:bold} QTabBar::tab{padding:8px 15px} QTableWidget{gridline-color:#d5d9dd}")

    def _show_admin_state(self):
        admin = is_admin()
        self.admin_button.setVisible(not admin)
        if admin:
            self.admin_banner.setText("Đang chạy với quyền quản trị")
            self.admin_banner.setStyleSheet("background:#d7f5df;color:#176b32;padding:8px")
        else:
            self.admin_banner.setText("Chế độ giới hạn: một số thông tin có thể hiển thị 'Không đủ quyền kiểm tra'.")
            self.admin_banner.setStyleSheet("background:#fff3cd;color:#725c00;padding:8px")

    def _apply_profile_catalog(self,catalog):
        mapping={"asset_code":"machine_types","department":"departments","location":"locations"}
        for field_key,catalog_key in mapping.items():
            field=self.fields[field_key];current=field.currentText().strip();field.blockSignals(True);field.clear()
            if field_key!="asset_code":field.addItem("")
            field.addItems(catalog.get(catalog_key,[]))
            index=field.findText(current,Qt.MatchFixedString)
            if index>=0:field.setCurrentIndex(index)
            field.blockSignals(False)

    def open_profile_template_settings(self):
        self._apply_profile_catalog(load_catalog())
        ProfileTemplateDialog(self,self._apply_profile_catalog).exec_()

    def elevate(self):
        if restart_as_admin():
            self.close()
        else:
            QMessageBox.warning(self, "Quyền quản trị", "Không thể cấp quyền quản trị. Ứng dụng tiếp tục ở chế độ giới hạn.")

    def metadata(self):
        return {**{k: (v.currentText() if isinstance(v,QComboBox) else v.text()).strip() for k, v in self.fields.items()}, "notes": self.notes.toPlainText().strip(), "audit_date": self.audit_date.date().toString("yyyy-MM-dd"), "audit_date_display": self.audit_date.date().toString("dd/MM/yyyy")}

    def _normalize_employee_code(self):
        field=self.fields["employee_code"];field.setText(normalize_employee_code(field.text()));self.validate_profile(show_message=False)

    def _clear_field_error(self,key):self.fields[key].setStyleSheet("")

    def validate_profile(self,show_message=True):
        result=validate_required_profile_fields(self.metadata())
        labels={label:key for key,label in REQUIRED_FIELDS}
        for key,_ in REQUIRED_FIELDS:self.fields[key].setStyleSheet("")
        for label in result["missing_fields"]:self.fields[labels[label]].setStyleSheet("border:2px solid #d00000")
        for item in result["invalid_fields"]:self.fields[item["key"]].setStyleSheet("border:2px solid #d00000")
        if result["normalized_profile"].get("employee_code")!=self.fields["employee_code"].text():self.fields["employee_code"].setText(result["normalized_profile"]["employee_code"])
        if not result["is_valid"] and show_message:
            lines=[f"- {x}" for x in result["missing_fields"]]+[f"- {x['field']}: {x['message']}" for x in result["invalid_fields"]]
            QMessageBox.warning(self,"CHƯA ĐỦ THÔNG TIN HỒ SƠ","Vui lòng nhập đầy đủ các trường bắt buộc trước khi cập nhật dữ liệu:\n\n"+"\n".join(lines));first=(result["missing_fields"][0] if result["missing_fields"] else result["invalid_fields"][0]["field"]);self.fields[labels.get(first,"employee_code")].setFocus()
        return result

    def start_scan(self):
        if not self.validate_profile()["is_valid"]:return
        if self.worker and self.worker.isRunning():
            return
        self.scan_button.setEnabled(False); self.rescan_button.setEnabled(False); self.progress.setValue(0)
        self.progress.setVisible(True)
        self.worker = AuditWorker(self.metadata(), self)
        self.worker.progress.connect(lambda p, s: (self.progress.setValue(p), self.status.setText(s)))
        self.worker.completed.connect(self.scan_completed)
        self.worker.failed.connect(lambda e: QMessageBox.critical(self, "Lỗi", e))
        self.worker.finished.connect(lambda: (self.scan_button.setEnabled(True), self.rescan_button.setEnabled(True), self.progress.setVisible(False)))
        self.worker.start()

    def scan_completed(self, result):
        self.last_result = result
        self.overview_tab.set_result(result); self.hardware_tab.set_result(result); self.windows_tab.set_result(result); self.network_tab.set_result(result); self.license_tab.set_result(result); self.export_tab.set_result(result)
        if result.errors:
            self.status.setText(f"Hoàn thành với {len(result.errors)} cảnh báo kỹ thuật")
        else:
            self.status.setText("Đã hoàn thành kiểm tra máy tính")
        self.export_management_csv(silent=True)
        if self.export_tab.auto.isChecked() and result.metadata.get("asset_code"):self.send_management_data(silent=True)

    def save_auto_export_setting(self,enabled):
        try:
            path=resource_path("config/app_config.json");data=json.loads(path.read_text(encoding="utf-8"));data.setdefault("google_sync",{})["auto_submit_after_scan"]=bool(enabled);atomic_json_write(path,data)
        except Exception: pass

    def export_management_csv(self,silent=False):
        result=self._ready_result()
        if not result:return
        try:
            path=export_admin_csv(result,Path(self.export_tab.folder.text()));self.export_tab.exported(path)
            if not silent:QMessageBox.information(self,"Xuất CSV",f"Đã xuất dữ liệu máy tính thành công.\n\nTên file:\n{path.name}\n\nVị trí:\n{path}")
        except Exception as exc:
            if silent:self.status.setText(f"Đã quét xong nhưng không thể tự động lưu CSV: {exc}")
            else:QMessageBox.warning(self,"Không thể xuất CSV",str(exc))

    def send_management_data(self,silent=False):
        if not self.last_result:
            QMessageBox.warning(self,"Gửi dữ liệu","Chưa có dữ liệu máy tính để gửi.\nVui lòng nhập thông tin hồ sơ và thực hiện quét máy tính trước.");return
        result=self._ready_result()
        if not result:return
        if not self.sync_service:
            self.export_tab.set_sync_status("NOT_CONFIGURED","Không thể khởi tạo dịch vụ đồng bộ.");return
        if self.sync_worker and self.sync_worker.isRunning():return
        self.export_tab.set_sync_status("ĐANG CẬP NHẬT",device_id=self.sync_service.identity.device_id,queue_count=self.sync_service.queue.count(),audit_id=result.audit_id)
        self.sync_worker=SubmitAuditWorker(self.sync_service,result,self);self.sync_worker.completed.connect(lambda response:self._submit_completed(response,result));self.sync_worker.failed.connect(lambda message:self.export_tab.set_sync_status("LỖI DỮ LIỆU",message,self.sync_service.identity.device_id,self.sync_service.queue.count(),result.audit_id));self.sync_worker.start()

    def _submit_completed(self,response,result):
        self.export_tab.set_sync_status(response.code,response.message,self.sync_service.identity.device_id,self.sync_service.queue.count(),result.audit_id,response.server_time);self.export_tab.status.setText(response.message or response.code)

    def retry_pending_data(self):
        if not self.sync_service or (self.retry_worker and self.retry_worker.isRunning()):return
        self.retry_worker=RetryQueueWorker(self.sync_service,False,self);self.retry_worker.completed.connect(lambda results:self.export_tab.set_sync_status(results[-1].code if results else "UP_TO_DATE",results[-1].message if results else "Không có dữ liệu chờ.",self.sync_service.identity.device_id,self.sync_service.queue.count()));self.retry_worker.failed.connect(lambda message:self.export_tab.set_sync_status("LỖI KẾT NỐI",message,self.sync_service.identity.device_id,self.sync_service.queue.count()));self.retry_worker.start()

    def retry_due_data(self):
        if not self.sync_service or (self.retry_worker and self.retry_worker.isRunning()):return
        self.retry_worker=RetryQueueWorker(self.sync_service,True,self);self.retry_worker.completed.connect(lambda _results:self.export_tab.set_sync_status("UP_TO_DATE","Đã kiểm tra hàng đợi ngoại tuyến.",self.sync_service.identity.device_id,self.sync_service.queue.count()));self.retry_worker.start()

    def _ready_result(self):
        if not self.validate_profile()["is_valid"]:return None
        if not self.last_result:
            QMessageBox.warning(self, "Xuất dữ liệu", "Vui lòng quét máy tính trước khi lưu hoặc xuất dữ liệu.")
            return None
        self.last_result.metadata = self.metadata()
        self.last_result.ip_plan = {key: field.text().strip() for key, field in self.network_tab.plan_fields.items()}
        return self.last_result

    @staticmethod
    def results_root():
        return Path.home() / "ATG_PC_AUDIT" / "Kết quả kiểm tra" # đổi tên đơn vị sử dụng

    def save_record(self):
        result = self._ready_result()
        if not result: return
        try:
            folder = save_complete_record(result, self.results_root())
            QMessageBox.information(self, "Lưu hồ sơ", f"Đã lưu hồ sơ đầy đủ tại:\n{folder}")
        except Exception as exc: QMessageBox.critical(self, "Lỗi lưu hồ sơ", str(exc))

    def export_excel(self):
        result = self._ready_result()
        if not result: return
        path, _ = QFileDialog.getSaveFileName(self, "Xuất Excel", str(self.results_root() / "audit_result.xlsx"), "Excel (*.xlsx)")
        if path:
            try: export_machine_excel(result, Path(path)); QMessageBox.information(self, "Xuất Excel", f"Đã xuất:\n{path}")
            except Exception as exc: QMessageBox.critical(self, "Lỗi xuất Excel", str(exc))

    def export_json(self):
        result = self._ready_result()
        if not result: return
        path, _ = QFileDialog.getSaveFileName(self, "Xuất JSON", str(self.results_root() / "audit_result.json"), "JSON (*.json)")
        if path:
            try: save_json(result, Path(path)); QMessageBox.information(self, "Xuất JSON", f"Đã xuất:\n{path}")
            except Exception as exc: QMessageBox.critical(self, "Lỗi xuất JSON", str(exc))

    def export_csv(self):
        result = self._ready_result()
        if not result: return
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu CSV", str(self.results_root()))
        if folder:
            try:
                export_network_csv(result, Path(folder) / "audit_network.csv"); export_license_csv(result, Path(folder) / "audit_license.csv")
                QMessageBox.information(self, "Xuất CSV", f"Đã xuất 2 file CSV tại:\n{folder}")
            except Exception as exc: QMessageBox.critical(self, "Lỗi xuất CSV", str(exc))

    def open_results(self):
        folder = self.results_root(); folder.mkdir(parents=True, exist_ok=True); QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

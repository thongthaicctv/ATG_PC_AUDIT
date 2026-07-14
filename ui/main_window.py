from PyQt5.QtCore import QDate, QUrl, Qt
from PyQt5.QtGui import QDesktopServices, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QDateEdit, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
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
from core.export_manager import export_license_csv, export_machine_excel, export_network_csv, save_complete_record, save_json
from core.csv_exporter import export_csv as export_admin_csv
from core.resource_utils import resource_path
import json
from pathlib import Path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.last_result = None
        self.setWindowTitle("ATG PC AUDIT – Kiểm tra máy tính và quy hoạch IP")
        self.setWindowIcon(QIcon(str(resource_path("assets/app.ico"))))
        self.setMinimumSize(960, 640)
        self.resize(1200, 720)
        self._build_ui()
        self._show_admin_state()

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
        brand_title = QLabel("ATG PC AUDIT")
        brand_title.setStyleSheet("font-size:20px;font-weight:700;color:#12376b")
        brand_subtitle = QLabel("Kiểm tra máy tính • Quy hoạch IP • Tổng hợp tài sản CNTT")
        brand_subtitle.setStyleSheet("color:#526575")
        brand_text.addWidget(brand_title); brand_text.addWidget(brand_subtitle)
        brand.addWidget(logo); brand.addLayout(brand_text); brand.addStretch()
        layout.addLayout(brand)
        self.admin_banner = QLabel()
        self.admin_banner.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.admin_banner)

        box = QGroupBox("Thông tin hồ sơ")
        grid = QGridLayout(box)
        self.fields = {name: QLineEdit() for name in ["asset_code", "user", "department", "location", "auditor"]}
        profile_hints = {
            "asset_code": "Ví dụ: ATG-LT-001 hoặc LAPTOP-001",
            "user": "Ví dụ: Bùi Duy Thông",
            "department": "Ví dụ: HCNS-CTV hoặc Phòng Kế toán",
            "location": "Ví dụ: Tầng 2 - Phòng 205",
            "auditor": "Ví dụ: Nguyễn Văn A",
        }
        for field in self.fields.values():
            field.setMinimumHeight(30)
            field.setMinimumWidth(180)
        for key, hint in profile_hints.items():
            self.fields[key].setPlaceholderText(hint)
            self.fields[key].setToolTip(hint)
        self.notes = QTextEdit(); self.notes.setMaximumHeight(55)
        self.notes.setMinimumHeight(48)
        self.notes.setPlaceholderText("Nhập ghi chú nhanh, ví dụ: Máy cần sao lưu dữ liệu trước khi cài lại Windows...")
        self.notes.setToolTip("Ghi chú tình trạng máy hoặc yêu cầu cần xử lý trước khi cài đặt.")
        self.audit_date = QDateEdit(); self.audit_date.setDisplayFormat("dd/MM/yyyy"); self.audit_date.setCalendarPopup(True); self.audit_date.setDate(QDate.currentDate()); self.audit_date.setMinimumHeight(30)
        self.audit_date.setToolTip("Chọn ngày thực hiện kiểm tra máy tính.")
        labels = [("Mã tài sản", "asset_code"), ("Người sử dụng", "user"), ("Phòng ban", "department"), ("Vị trí đặt máy", "location"), ("Người thực hiện", "auditor")]
        for i, (title, key) in enumerate(labels):
            grid.addWidget(QLabel(title), i // 3 * 2, i % 3)
            grid.addWidget(self.fields[key], i // 3 * 2 + 1, i % 3)
        grid.addWidget(QLabel("Ngày kiểm tra"), 2, 2); grid.addWidget(self.audit_date, 3, 2)
        grid.addWidget(QLabel("Ghi chú"), 4, 0); grid.addWidget(self.notes, 5, 0, 1, 3)
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
        self.export_tab.export_requested.connect(self.export_management_csv); self.export_tab.auto_changed.connect(self.save_auto_export_setting)
        try:
            cfg=json.loads(resource_path("config/app_config.json").read_text(encoding="utf-8"));self.export_tab.auto.setChecked(bool(cfg.get("auto_export_csv",True)))
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

    def elevate(self):
        if restart_as_admin():
            self.close()
        else:
            QMessageBox.warning(self, "Quyền quản trị", "Không thể cấp quyền quản trị. Ứng dụng tiếp tục ở chế độ giới hạn.")

    def metadata(self):
        return {**{k: v.text().strip() for k, v in self.fields.items()}, "notes": self.notes.toPlainText().strip(), "audit_date": self.audit_date.date().toString("yyyy-MM-dd"), "audit_date_display": self.audit_date.date().toString("dd/MM/yyyy")}

    def start_scan(self):
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
        if self.export_tab.auto.isChecked() and result.metadata.get("asset_code"):
            self.export_management_csv(silent=True)

    def save_auto_export_setting(self,enabled):
        try:
            path=resource_path("config/app_config.json");data=json.loads(path.read_text(encoding="utf-8"));data["auto_export_csv"]=bool(enabled);path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception: pass

    def export_management_csv(self,silent=False):
        result=self._ready_result()
        if not result:return
        try:
            path=export_admin_csv(result,Path(self.export_tab.folder.text()));self.export_tab.exported(path)
            if not silent:QMessageBox.information(self,"Xuất CSV",f"Đã xuất dữ liệu máy tính thành công.\n\nTên file:\n{path.name}\n\nVị trí:\n{path}")
        except Exception as exc:
            if not silent:QMessageBox.warning(self,"Không thể xuất CSV",str(exc))

    def _ready_result(self):
        if not self.last_result:
            QMessageBox.warning(self, "Xuất dữ liệu", "Vui lòng quét máy tính trước khi lưu hoặc xuất dữ liệu.")
            return None
        self.last_result.metadata = self.metadata()
        self.last_result.ip_plan = {key: field.text().strip() for key, field in self.network_tab.plan_fields.items()}
        return self.last_result

    @staticmethod
    def results_root():
        return Path.home() / "ATG_PC_AUDIT" / "KetQuaKiemTra"

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

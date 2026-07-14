from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFormLayout, QGroupBox, QHeaderView, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)


class LicenseTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        windows_page = QWidget(); windows_layout = QVBoxLayout(windows_page)
        windows_box = QGroupBox("Bản quyền Windows – chỉ đọc")
        self.windows_form = QFormLayout(windows_box); self.windows_labels = {}
        self.technical = QTextEdit(); self.technical.setReadOnly(True); self.technical.setVisible(False); self.technical.setMaximumHeight(130)
        technical_button = QPushButton("XEM / ẨN DỮ LIỆU KỸ THUẬT")
        technical_button.clicked.connect(lambda: self.technical.setVisible(not self.technical.isVisible()))
        windows_layout.addWidget(windows_box); windows_layout.addWidget(technical_button); windows_layout.addWidget(self.technical); windows_layout.addStretch()

        office_page = QWidget(); office_layout = QVBoxLayout(office_page)
        self.products = QTableWidget(0, 7)
        self.products.setHorizontalHeaderLabels(["Sản phẩm", "Phiên bản", "Nền tảng", "Kiểu cài", "Kênh cập nhật", "Đường dẫn", "Release ID"])
        self.licenses = QTableWidget(0, 7)
        self.licenses.setHorizontalHeaderLabels(["Sản phẩm", "Trạng thái", "Cơ chế", "Partial Key", "Raw Status", "Tài khoản cục bộ", "Ghi chú"])
        for table in (self.products, self.licenses):
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            table.horizontalHeader().setStretchLastSection(True)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setMinimumHeight(190)
        office_layout.addWidget(QLabel("Sản phẩm Office đã phát hiện")); office_layout.addWidget(self.products)
        office_layout.addWidget(QLabel("Trạng thái bản quyền từng sản phẩm")); office_layout.addWidget(self.licenses)
        tabs.addTab(windows_page, "Windows"); tabs.addTab(office_page, "Office / Microsoft 365")
        root.addWidget(tabs)
        warning = QLabel("Ứng dụng chỉ đọc trạng thái hiện tại, không xác nhận tính hợp pháp của nguồn key; không kích hoạt, không thay đổi hoặc xóa license. Email/Tenant Office chỉ hiển thị cục bộ và mặc định không xuất file.")
        warning.setWordWrap(True); warning.setStyleSheet("background:#fff3cd;color:#6b5200;padding:8px")
        root.addWidget(warning)

    def set_result(self, result):
        while self.windows_form.rowCount(): self.windows_form.removeRow(0)
        self.windows_labels.clear()
        fields = [
            ("edition", "Phiên bản Windows"), ("activation_status", "Trạng thái kích hoạt"),
            ("license_channel", "Kênh bản quyền"), ("license_type", "Loại giấy phép"),
            ("partial_key", "Product key đã che"), ("oem_key_present", "Có khóa OEM trong BIOS"),
            ("oem_key_last5", "Khóa OEM đã che"), ("permanent_activation", "Kích hoạt vĩnh viễn"),
            ("expiration", "Ngày hết hạn"), ("grace_remaining_minutes", "Grace còn lại (phút)"),
            ("license_status_reason", "License Status Reason"),
        ]
        for key, title in fields:
            value = result.windows_license.get(key, "Không xác định")
            if isinstance(value, bool): value = "Có" if value else "Không"
            if value is None: value = "Không xác định"
            label = QLabel(str(value)); label.setTextInteractionFlags(label.textInteractionFlags() | 1)
            if key == "activation_status":
                label.setStyleSheet("font-weight:bold;color:" + ("#17723b" if value == "Đã kích hoạt" else "#b42318"))
            self.windows_form.addRow(f"{title}:", label); self.windows_labels[key] = label
        self.technical.setPlainText("\n".join(f"{k}: {v}" for k, v in result.windows_license.items() if k not in ("partial_key", "oem_key_last5")) + "\nProduct key: " + str(result.windows_license.get("partial_key", "Không có")))

        product_keys = ["product_name", "version", "platform", "install_type", "update_channel", "installation_path", "release_id"]
        self.products.setRowCount(len(result.office_products))
        for row, product in enumerate(result.office_products):
            for col, key in enumerate(product_keys): self.products.setItem(row, col, QTableWidgetItem(str(product.get(key, "Không xác định"))))
        license_keys = ["product_name", "activation_status", "mechanism", "partial_key", "raw_status", "account", "note"]
        self.licenses.setRowCount(len(result.office_licenses))
        status_colors = {"Đã kích hoạt": QColor("#d7f5df"), "Chưa kích hoạt": QColor("#ffd9d5"), "Hết hạn": QColor("#ffd9d5"), "Đang trong thời gian Grace": QColor("#fff3cd"), "Không thể xác định": QColor("#fff3cd"), "Không có Office": QColor("#eeeeee")}
        for row, license_item in enumerate(result.office_licenses):
            display = dict(license_item)
            display["account"] = " | ".join(x for x in (str(display.get("user_email", "")), str(display.get("tenant_id", ""))) if x) or "Không có"
            for col, key in enumerate(license_keys):
                item = QTableWidgetItem(str(display.get(key, "Không xác định")))
                item.setBackground(status_colors.get(display.get("activation_status"), QColor("white")))
                self.licenses.setItem(row, col, item)

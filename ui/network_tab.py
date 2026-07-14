from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
    QHeaderView,
)

from core.network_collector import validate_ip_plan


class NetworkTab(QWidget):
    COLUMNS = [
        ("name", "Tên card"), ("interface_type", "Loại"), ("connection_status", "Kết nối"),
        ("mac_address", "MAC Address"), ("ipv4", "IPv4"), ("prefix_or_mask", "Prefix/Mask"),
        ("default_gateway", "Gateway"), ("dns_servers", "DNS"), ("dhcp_enabled", "DHCP"),
        ("dhcp_server", "DHCP Server"), ("link_speed_mbps", "Mbps"), ("interface_index", "Interface Index"),
        ("manufacturer", "Hãng"), ("driver_version", "Driver"),
    ]

    def __init__(self):
        super().__init__()
        self.result = None
        self.adapters_by_index = {}
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Card mạng chính dùng cho quy hoạch IP:"))
        self.primary_combo = QComboBox(); self.primary_combo.currentIndexChanged.connect(self._primary_changed)
        self.primary_combo.setMinimumWidth(420)
        top.addWidget(self.primary_combo, 1)
        layout.addLayout(top)

        tabs = QTabWidget()
        tabs.setMinimumHeight(245)
        self.physical_table = self._table()
        self.other_table = self._table()
        tabs.addTab(self.physical_table, "Ethernet / Wi-Fi vật lý")
        tabs.addTab(self.other_table, "Card mạng khác")
        layout.addWidget(tabs, 1)

        plan = QGroupBox("Quy hoạch IP dự kiến – chỉ ghi nhận, không thay đổi cấu hình máy")
        grid = QGridLayout(plan)
        fields = ["vlan", "planned_ip", "prefix", "gateway", "dns1", "dns2", "switch_name", "switch_port", "network_socket", "deployment_status", "notes"]
        titles = ["VLAN dự kiến", "IP dự kiến", "Prefix", "Gateway dự kiến", "DNS 1", "DNS 2", "Tên switch", "Cổng switch", "Ổ cắm mạng", "Trạng thái triển khai", "Ghi chú"]
        self.plan_fields = {key: QLineEdit() for key in fields}
        plan_hints = {
            "vlan": "Ví dụ: VLAN 20 hoặc 20",
            "planned_ip": "Ví dụ: 192.168.20.15",
            "prefix": "Ví dụ: 24",
            "gateway": "Ví dụ: 192.168.20.1",
            "dns1": "Ví dụ: 192.168.1.10",
            "dns2": "Ví dụ: 8.8.8.8",
            "switch_name": "Ví dụ: SW-TANG2-01",
            "switch_port": "Ví dụ: Gi1/0/12",
            "network_socket": "Ví dụ: T2-P205-01",
            "deployment_status": "Ví dụ: Chờ triển khai / Đã triển khai",
            "notes": "Ví dụ: Giữ IP cho máy kế toán",
        }
        for field in self.plan_fields.values():
            field.setMinimumHeight(30)
            field.setMinimumWidth(180)
        for key, hint in plan_hints.items():
            self.plan_fields[key].setPlaceholderText(hint)
            self.plan_fields[key].setToolTip(hint)
        self.plan_fields["prefix"].setText("24")
        for i, (key, title) in enumerate(zip(fields, titles)):
            row, col = divmod(i, 3)
            grid.addWidget(QLabel(title), row * 2, col)
            grid.addWidget(self.plan_fields[key], row * 2 + 1, col)
        for col in range(3):
            grid.setColumnStretch(col, 1)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(5)
        actions = QHBoxLayout()
        copy_button = QPushButton("SAO CHÉP IP HIỆN TẠI SANG IP DỰ KIẾN")
        check_button = QPushButton("KIỂM TRA IP DỰ KIẾN")
        copy_button.clicked.connect(self.copy_current_ip); check_button.clicked.connect(self.validate_plan)
        self.validation_label = QLabel("Chưa kiểm tra")
        actions.addWidget(copy_button); actions.addWidget(check_button); actions.addWidget(self.validation_label, 1)
        grid.addLayout(actions, 8, 0, 1, 3)
        layout.addWidget(plan)

    def _table(self):
        table = QTableWidget(0, len(self.COLUMNS))
        table.setHorizontalHeaderLabels([x[1] for x in self.COLUMNS])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        widths = [165, 115, 90, 145, 125, 115, 125, 130, 75, 120, 80, 105, 130, 110]
        for index, width in enumerate(widths):
            table.setColumnWidth(index, width)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setMinimumHeight(185)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        return table

    @staticmethod
    def _display(value):
        if isinstance(value, list):
            return ", ".join(str(x) for x in value) or "Không có"
        if value is None:
            return "Không xác định"
        return str(value)

    def _fill(self, table, adapters):
        table.setRowCount(len(adapters))
        for row, adapter in enumerate(adapters):
            for col, (key, _) in enumerate(self.COLUMNS):
                item = QTableWidgetItem(self._display(adapter.get(key)))
                if key == "mac_address":
                    item.setFont(table.font()); item.setForeground(QColor("#0b57a4"))
                table.setItem(row, col, item)

    def set_result(self, result):
        self.result = result
        physical = [x for x in result.network_adapters if x.get("interface_type") in ("Ethernet vật lý", "Wi-Fi vật lý")]
        others = [x for x in result.network_adapters if x not in physical]
        self._fill(self.physical_table, physical); self._fill(self.other_table, others)
        self.adapters_by_index = {x.get("interface_index"): x for x in physical}
        self.primary_combo.blockSignals(True); self.primary_combo.clear()
        for adapter in physical:
            label = f"{adapter['name']} | {adapter['mac_address']} | {self._display(adapter['ipv4'])}"
            self.primary_combo.addItem(label, adapter.get("interface_index"))
        selected = self.primary_combo.findData(result.primary_adapter_index)
        if selected >= 0: self.primary_combo.setCurrentIndex(selected)
        self.primary_combo.blockSignals(False)

    def _primary_changed(self):
        if self.result and self.primary_combo.currentIndex() >= 0:
            self.result.primary_adapter_index = self.primary_combo.currentData()

    def current_adapter(self):
        return self.adapters_by_index.get(self.primary_combo.currentData())

    def copy_current_ip(self):
        adapter = self.current_adapter()
        if not adapter or not adapter.get("ipv4"):
            QMessageBox.warning(self, "Quy hoạch IP", "Card mạng chính không có IPv4 hợp lệ.")
            return
        self.plan_fields["planned_ip"].setText(adapter["ipv4"][0])
        gateways = adapter.get("default_gateway") or []
        dns = adapter.get("dns_servers") or []
        if gateways: self.plan_fields["gateway"].setText(gateways[0])
        if dns: self.plan_fields["dns1"].setText(dns[0])
        if len(dns) > 1: self.plan_fields["dns2"].setText(dns[1])

    def validate_plan(self):
        ok, message = validate_ip_plan(self.plan_fields["planned_ip"].text().strip(), self.plan_fields["prefix"].text().strip(), self.plan_fields["gateway"].text().strip())
        self.validation_label.setText(message)
        self.validation_label.setStyleSheet(f"color:{'#17723b' if ok else '#b42318'};font-weight:bold")
        if self.result:
            self.result.ip_plan = {key: field.text().strip() for key, field in self.plan_fields.items()}
            self.result.ip_plan["valid"] = ok
        return ok

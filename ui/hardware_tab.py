from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget


def _fill(table, rows):
    table.setRowCount(len(rows))
    for r, (name, value) in enumerate(rows):
        table.setItem(r, 0, QTableWidgetItem(str(name)))
        table.setItem(r, 1, QTableWidgetItem(str(value)))


class HardwareTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        self.computer = self._pair_table()
        self.cpu = self._pair_table()
        self.bios = self._pair_table()
        self.ram = QTableWidget(0, 8)
        self.ram.setHorizontalHeaderLabels(["Slot", "Bank", "GB", "Tốc độ", "Clock cấu hình", "Hãng", "Part Number", "Serial"])
        self.ram.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ram.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.disks = QTableWidget(0, 9)
        self.disks.setHorizontalHeaderLabels(["Index", "Model", "Serial", "Bus", "Media", "Loại", "MBR/GPT", "Dung lượng GB", "Trạng thái"])
        self.disks.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.disks.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.gpu = QTableWidget(0, 9)
        self.gpu.setHorizontalHeaderLabels(["STT", "Tên card đồ họa", "Bộ xử lý", "VRAM GB", "Driver", "Ngày driver", "Độ phân giải", "Trạng thái", "Đang sử dụng"])
        self.gpu.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.gpu.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.gpu.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.network = QTableWidget(0, 7)
        self.network.setHorizontalHeaderLabels(["Card mạng", "Loại", "Kết nối", "MAC Address", "IPv4", "Gateway", "Card chính"])
        self.network.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.network.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        tabs.addTab(self.computer, "Máy tính")
        tabs.addTab(self.cpu, "CPU")
        tabs.addTab(self.ram, "RAM")
        tabs.addTab(self.bios, "BIOS & Mainboard")
        tabs.addTab(self.disks, "Ổ đĩa")
        tabs.addTab(self.gpu, "Card đồ họa")
        tabs.addTab(self.network, "Card mạng")
        layout.addWidget(tabs)

    @staticmethod
    def _pair_table():
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Thuộc tính", "Giá trị"])
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        return table

    def set_result(self, result):
        _fill(self.computer, [(k, v) for k, v in result.computer.items()])
        _fill(self.cpu, [(k, v) for k, v in result.cpu.items()])
        _fill(self.bios, [(k, v) for k, v in result.bios.items()] + [(k, v) for k, v in result.security.items()])
        self.ram.setRowCount(len(result.ram_modules))
        keys = ["slot", "bank", "capacity_gb", "speed_mhz", "configured_clock_mhz", "manufacturer", "part_number", "serial_number"]
        for row, module in enumerate(result.ram_modules):
            for col, key in enumerate(keys):
                self.ram.setItem(row, col, QTableWidgetItem(str(module.get(key, "Không xác định"))))
        disk_keys = ["disk_index", "model", "serial_number", "bus_type", "media_type", "disk_type", "partition_style", "capacity_gb", "status"]
        self.disks.setRowCount(len(result.disks))
        for row, disk in enumerate(result.disks):
            for col, key in enumerate(disk_keys):
                self.disks.setItem(row, col, QTableWidgetItem(str(disk.get(key, "Không xác định"))))
        gpu_keys = ["gpu_index", "name", "video_processor", "adapter_ram_gb", "driver_version", "driver_date", "resolution", "status"]
        self.gpu.setRowCount(len(result.gpu))
        for row, gpu in enumerate(result.gpu):
            for col, key in enumerate(gpu_keys):
                value = row + 1 if key == "gpu_index" else gpu.get(key, "Không xác định")
                self.gpu.setItem(row, col, QTableWidgetItem(str(value)))
            self.gpu.setItem(row, 8, QTableWidgetItem("Có" if gpu.get("is_active") else ""))
        self.network.setRowCount(len(result.network_adapters))
        network_keys = ["name", "interface_type", "connection_status", "mac_address", "ipv4", "default_gateway"]
        for row, adapter in enumerate(result.network_adapters):
            for col, key in enumerate(network_keys):
                value = adapter.get(key, "Không xác định")
                if isinstance(value, list): value = ", ".join(value) or "Không có"
                self.network.setItem(row, col, QTableWidgetItem(str(value)))
            primary = adapter.get("interface_index") == result.primary_adapter_index
            self.network.setItem(row, 6, QTableWidgetItem("Có" if primary else ""))

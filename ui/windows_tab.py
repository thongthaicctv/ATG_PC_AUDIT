from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QFormLayout, QHeaderView, QLabel, QListWidget, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget


class WindowsTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        info = QWidget(); self.layout = QFormLayout(info)
        self.labels = {}
        readiness = QWidget(); ready_layout = QVBoxLayout(readiness)
        self.overall = QLabel("Chưa quét"); self.overall.setStyleSheet("font-size:18px;font-weight:bold;padding:10px")
        self.conditions = QTableWidget(0, 5)
        self.conditions.setHorizontalHeaderLabels(["Điều kiện", "Giá trị thực tế", "Yêu cầu", "Trạng thái", "Ghi chú"])
        self.conditions.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recommendations = QListWidget()
        ready_layout.addWidget(self.overall); ready_layout.addWidget(self.conditions, 1); ready_layout.addWidget(QLabel("Khuyến nghị")); ready_layout.addWidget(self.recommendations)
        self.tabs.addTab(info, "Windows hiện tại"); self.tabs.addTab(readiness, "Windows 11")
        root.addWidget(self.tabs)

    def set_result(self, result):
        while self.layout.rowCount():
            self.layout.removeRow(0)
        self.labels.clear()
        for key, value in result.windows.items():
            label = QLabel(str(value))
            label.setTextInteractionFlags(label.textInteractionFlags() | 1)
            self.layout.addRow(f"{key}:", label)
            self.labels[key] = label
        readiness = result.windows11
        self.overall.setText(readiness.get("display_overall", readiness.get("overall", "CẦN KIỂM TRA THÊM")))
        overall_color = "#1f7a3d" if readiness.get("overall", "").startswith("ĐỦ") else ("#b42318" if readiness.get("overall", "").startswith("KHÔNG") else "#8a6500")
        self.overall.setStyleSheet(f"font-size:18px;font-weight:bold;padding:10px;color:{overall_color}")
        rows = readiness.get("conditions", [])
        self.conditions.setRowCount(len(rows))
        colors = {"Đạt": QColor("#d7f5df"), "Không đạt": QColor("#ffd9d5"), "Chưa xác định": QColor("#fff3cd"), "Khuyến nghị bật": QColor("#fff3cd")}
        keys = ["condition", "actual", "required", "status", "note"]
        for row, condition in enumerate(rows):
            for col, key in enumerate(keys):
                item = QTableWidgetItem(str(condition.get(key, "")))
                item.setBackground(colors.get(condition.get("status"), QColor("#eeeeee")))
                self.conditions.setItem(row, col, item)
        self.recommendations.clear(); self.recommendations.addItems(result.recommendations or ["Không có khuyến nghị bổ sung."])

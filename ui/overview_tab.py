from PyQt5.QtWidgets import QFormLayout, QLabel, QWidget


class OverviewTab(QWidget):
    FIELDS = [
        ("computer_name", "Tên máy"), ("asset_code", "Mã tài sản"),
        ("windows_user", "Người sử dụng Windows"), ("manufacturer", "Hãng máy"),
        ("model", "Model"), ("serial_number", "Serial Number"),
        ("windows", "Windows đang sử dụng"), ("ram", "Tổng RAM"),
        ("tpm", "TPM"), ("secure_boot", "Secure Boot"),
        ("windows11", "Khả năng cài Windows 11"),
        ("primary_ip", "IP đang sử dụng"), ("primary_mac", "MAC Address chính"),
        ("windows_activation", "Trạng thái Windows"), ("office_activation", "Trạng thái Office"),
    ]

    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        self.labels = {}
        for key, title in self.FIELDS:
            label = QLabel("Chưa quét")
            label.setTextInteractionFlags(label.textInteractionFlags() | 1)
            layout.addRow(f"{title}:", label)
            self.labels[key] = label

    def set_result(self, result):
        c = result.computer
        values = dict(c)
        values["asset_code"] = result.metadata.get("asset_code") or "Chưa nhập"
        values["windows"] = f"{result.windows.get('edition', 'Không xác định')} (Build {result.windows.get('build_number', '?')})"
        values["ram"] = f"{result.ram_summary.get('total_gb', '?')} GB"
        values["tpm"] = f"Present={result.security.get('tpm_present')}, Version={result.security.get('tpm_spec_version')}"
        values["secure_boot"] = "Đã bật" if result.security.get("secure_boot_enabled") else ("Đang tắt" if result.security.get("secure_boot_enabled") is False else "Không xác định")
        values["windows11"] = result.windows11.get("display_overall", result.windows11.get("overall", "Cần kiểm tra thêm"))
        primary = next((x for x in result.network_adapters if x.get("interface_index") == result.primary_adapter_index), {})
        values["primary_ip"] = ", ".join(primary.get("ipv4", [])) or "Không xác định"
        values["primary_mac"] = primary.get("mac_address", "Không xác định")
        values["windows_activation"] = result.windows_license.get("activation_status", "Không xác định")
        office_statuses = [x.get("activation_status", "Không thể xác định") for x in result.office_licenses]
        values["office_activation"] = ", ".join(dict.fromkeys(office_statuses)) or "Không có Office"
        for key, label in self.labels.items():
            label.setText(str(values.get(key, "Không xác định")))

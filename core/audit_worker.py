import logging

from PyQt5.QtCore import QThread, pyqtSignal

from core.hardware_collector import collect_bios, collect_computer, collect_cpu, collect_disks, collect_gpu, collect_ram, collect_security
from core.win11_checker import evaluate_windows11
from core.network_collector import collect_network
from core.windows_license_checker import collect_windows_license
from core.office_detector import detect_office
from core.office_license_checker import check_office_licenses
from core.windows_collector import collect_windows
from models.audit_result import AuditResult

LOG = logging.getLogger(__name__)


class AuditWorker(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, metadata=None, parent=None):
        super().__init__(parent)
        self.metadata = metadata or {}

    def run(self):
        result = AuditResult(metadata=self.metadata)
        steps = [
            (15, "Đang kiểm tra thông tin máy...", "computer", collect_computer),
            (40, "Đang kiểm tra CPU...", "cpu", collect_cpu),
            (70, "Đang kiểm tra RAM...", "ram", collect_ram),
            (78, "Đang kiểm tra BIOS...", "bios", collect_bios),
            (84, "Đang kiểm tra ổ đĩa...", "disks", collect_disks),
            (87, "Đang kiểm tra card đồ họa...", "gpu", collect_gpu),
            (90, "Đang kiểm tra TPM và Secure Boot...", "security", collect_security),
            (95, "Đang kiểm tra Windows...", "windows", collect_windows),
            (97, "Đang kiểm tra card mạng và MAC Address...", "network", collect_network),
            (98, "Đang kiểm tra bản quyền Windows...", "windows_license", collect_windows_license),
            (99, "Đang phát hiện Office...", "office_products", detect_office),
        ]
        for percent, message, target, collector in steps:
            self.progress.emit(percent, message)
            try:
                value = collector()
                if target == "ram":
                    result.ram_summary, result.ram_modules = value
                elif target == "network":
                    result.network_adapters, result.primary_adapter_index = value
                else:
                    setattr(result, target, value)
            except Exception as exc:
                LOG.exception("Lỗi khi %s", message.lower())
                result.errors.append(f"{message}: {exc}")
        self.progress.emit(98, "Đang đánh giá khả năng cài Windows 11...")
        if result.windows.get("edition") and result.windows_license:
            result.windows_license["edition"] = result.windows["edition"]
        try:
            result.windows11, result.recommendations = evaluate_windows11(result)
        except Exception as exc:
            LOG.exception("Lỗi đánh giá Windows 11")
            result.errors.append(f"Đánh giá Windows 11: {exc}")
        self.progress.emit(99, "Đang kiểm tra bản quyền Office...")
        try:
            result.office_licenses = check_office_licenses(result.office_products)
        except Exception as exc:
            LOG.exception("Lỗi kiểm tra bản quyền Office")
            result.errors.append(f"Kiểm tra bản quyền Office: {exc}")
        self.progress.emit(100, "Đã hoàn thành kiểm tra máy tính")
        self.completed.emit(result)

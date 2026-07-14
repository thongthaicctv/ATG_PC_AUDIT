import json
import re
from typing import Any, Dict, List, Tuple

from core.resource_utils import resource_path

PASS = "Đạt"
FAIL = "Không đạt"
UNKNOWN = "Chưa xác định"


def _condition(name, actual, required, status, note="", required_for_overall=True):
    return {"condition": name, "actual": actual, "required": required, "status": status, "note": note, "required_for_overall": required_for_overall}


def _bool_status(value) -> str:
    return UNKNOWN if value is None else (PASS if value else FAIL)


def _version_at_least_2(value) -> str:
    found = re.findall(r"\d+(?:\.\d+)?", str(value))
    if not found:
        return UNKNOWN
    return PASS if max(float(x) for x in found) >= 2.0 else FAIL


def _cpu_supported(cpu_name: str) -> Tuple[str, str]:
    try:
        data = json.loads(resource_path("config/supported_cpu_windows11.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return UNKNOWN, "Không đọc được cơ sở dữ liệu CPU"
    normalized = re.sub(r"[^a-z0-9]+", "", cpu_name.lower())
    entries = [str(x) for vendor in ("intel", "amd", "qualcomm") for x in data.get(vendor, [])]
    for entry in entries:
        if re.sub(r"[^a-z0-9]+", "", entry.lower()) in normalized:
            return PASS, f"Khớp cơ sở dữ liệu: {entry}"
    return UNKNOWN, "CPU chưa có trong cơ sở dữ liệu – cần kiểm tra thủ công"


def evaluate_windows11(result) -> Tuple[Dict[str, Any], List[str]]:
    cpu, ram, windows, security = result.cpu, result.ram_summary, result.windows, result.security
    system_disk = next((x for x in result.disks if x.get("is_system")), result.disks[0] if result.disks else {})
    cpu_db_status, cpu_db_note = _cpu_supported(str(cpu.get("name", "")))
    architecture = str(cpu.get("architecture", ""))
    conditions = [
        _condition("CPU 64-bit", architecture, "64-bit", PASS if "64" in architecture else FAIL),
        _condition("Số nhân CPU", cpu.get("cores"), ">= 2", PASS if isinstance(cpu.get("cores"), int) and cpu["cores"] >= 2 else (FAIL if cpu.get("cores") is not None else UNKNOWN)),
        _condition("Tốc độ CPU", cpu.get("max_clock_mhz"), ">= 1000 MHz", PASS if isinstance(cpu.get("max_clock_mhz"), (int, float)) and cpu["max_clock_mhz"] >= 1000 else (FAIL if isinstance(cpu.get("max_clock_mhz"), (int, float)) else UNKNOWN)),
        _condition("CPU trong danh sách hỗ trợ", cpu.get("name", "Không xác định"), "Danh sách Microsoft Windows 11", cpu_db_status, cpu_db_note),
        _condition("RAM", ram.get("total_gb"), ">= 4 GB", PASS if (ram.get("total_gb") or 0) >= 4 else FAIL),
        _condition("Dung lượng ổ hệ thống", windows.get("system_drive_total_gb"), ">= 64 GB", PASS if (windows.get("system_drive_total_gb") or 0) >= 64 else FAIL),
        _condition("Firmware UEFI", security.get("firmware_mode"), "UEFI", PASS if security.get("firmware_mode") == "UEFI" else (FAIL if security.get("firmware_mode") else UNKNOWN)),
        _condition("Secure Boot Capable", security.get("secure_boot_capable"), "Có", _bool_status(security.get("secure_boot_capable")), security.get("secure_boot_note", "")),
        _condition("Secure Boot Enabled", security.get("secure_boot_enabled"), "Khuyến nghị bật", PASS if security.get("secure_boot_enabled") is True else ("Khuyến nghị bật" if security.get("secure_boot_enabled") is False else UNKNOWN), "Microsoft yêu cầu Secure Boot capable; trạng thái Enabled được hiển thị để khuyến nghị.", False),
        _condition("TPM Present", security.get("tpm_present"), "Có", _bool_status(security.get("tpm_present")), security.get("tpm_note", "")),
        _condition("TPM Enabled", security.get("tpm_enabled"), "Bật", _bool_status(security.get("tpm_enabled")), security.get("tpm_note", "")),
        _condition("TPM Ready", security.get("tpm_ready"), "Sẵn sàng", _bool_status(security.get("tpm_ready")), security.get("tpm_note", "")),
        _condition("TPM Spec Version", security.get("tpm_spec_version"), ">= 2.0", _version_at_least_2(security.get("tpm_spec_version"))),
        _condition("Ổ hệ thống GPT", system_disk.get("partition_style", "Không xác định"), "GPT", PASS if str(system_disk.get("partition_style", "")).upper() == "GPT" else (FAIL if system_disk else UNKNOWN)),
    ]
    statuses = [x["status"] for x in conditions if x.get("required_for_overall", True)]
    overall = "KHÔNG ĐỦ ĐIỀU KIỆN CÀI WINDOWS 11" if FAIL in statuses else ("CẦN KIỂM TRA THÊM" if UNKNOWN in statuses else "ĐỦ ĐIỀU KIỆN CÀI WINDOWS 11")
    if windows.get("is_windows11"):
        display_overall = "MÁY ĐANG CHẠY WINDOWS 11"
        if overall == "CẦN KIỂM TRA THÊM":
            display_overall += " – CẦN KIỂM TRA THÊM DỮ LIỆU TPM/PHẦN CỨNG"
        elif overall.startswith("KHÔNG"):
            display_overall += " – CÓ ĐIỀU KIỆN KHÔNG ĐẠT CHUẨN CHÍNH THỨC"
        else:
            display_overall += " – ĐẠT CÁC ĐIỀU KIỆN ĐÃ KIỂM TRA"
    else:
        display_overall = overall
    recommendations: List[str] = []
    if (ram.get("total_gb") or 0) < 8:
        recommendations.append("Khuyến nghị nâng RAM tối thiểu 8 GB.")
    if system_disk.get("disk_type") == "HDD":
        recommendations.append("Khuyến nghị thay SSD cho ổ hệ thống.")
    if (windows.get("system_drive_free_gb") or 0) < 30:
        recommendations.append("Cần giải phóng hoặc nâng cấp ổ hệ thống do ổ C còn dưới 30 GB.")
    if security.get("tpm_present") and not security.get("tpm_enabled"):
        recommendations.append("Kiểm tra và bật TPM trong BIOS.")
    if security.get("secure_boot_capable") and not security.get("secure_boot_enabled"):
        recommendations.append("Kiểm tra UEFI và bật Secure Boot.")
    if cpu_db_status == FAIL:
        recommendations.append("CPU không hỗ trợ; cần nâng cấp hoặc thay máy.")
    elif cpu_db_status == UNKNOWN:
        recommendations.append("Cần kiểm tra thủ công CPU trong danh sách hỗ trợ Windows 11.")
    if overall == "KHÔNG ĐỦ ĐIỀU KIỆN CÀI WINDOWS 11":
        recommendations.append("Máy không đạt Windows 11; không khuyến nghị bypass yêu cầu phần cứng.")
    return {"overall": overall, "display_overall": display_overall, "current_os_is_windows11": bool(windows.get("is_windows11")), "conditions": conditions}, recommendations

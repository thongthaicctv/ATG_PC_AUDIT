import datetime as dt
import logging
import platform
import winreg
from typing import Any, Dict

import psutil

LOG = logging.getLogger(__name__)


def _reg_value(key, name, default="Không xác định"):
    try:
        return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return default


def collect_windows() -> Dict[str, Any]:
    path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    data: Dict[str, Any] = {}
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            data = {
                "edition": _reg_value(key, "ProductName"),
                "display_version": _reg_value(key, "DisplayVersion"),
                "version": _reg_value(key, "ReleaseId"),
                "build_number": str(_reg_value(key, "CurrentBuildNumber", platform.version())),
                "registered_owner": _reg_value(key, "RegisteredOwner"),
                "installation_date": _reg_value(key, "InstallDate"),
            }
    except OSError:
        LOG.exception("Không đọc được thông tin Windows trong Registry")
    install = data.get("installation_date")
    if isinstance(install, int):
        data["installation_date"] = dt.datetime.fromtimestamp(install).strftime("%d/%m/%Y")
    drive = psutil.disk_usage("C:\\")
    try:
        build_number = int(str(data.get("build_number", "0")).split(".")[0])
    except ValueError:
        build_number = 0
    is_windows11 = build_number >= 22000
    if is_windows11 and str(data.get("edition", "")).startswith("Windows 10"):
        data["edition"] = str(data["edition"]).replace("Windows 10", "Windows 11", 1)
    data.update({
        "architecture": platform.architecture()[0],
        "system_drive": "C:",
        "system_drive_total_gb": round(drive.total / 1024**3, 2),
        "system_drive_free_gb": round(drive.free / 1024**3, 2),
        "is_windows11": is_windows11,
    })
    return data

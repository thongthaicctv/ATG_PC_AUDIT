import logging
import re
import winreg
from typing import Any, Dict, List

LOG = logging.getLogger(__name__)


def _value(key, name, default=""):
    try: return winreg.QueryValueEx(key, name)[0]
    except OSError: return default


def _office_name(text: str) -> str:
    upper = text.upper()
    if "VISIO" in upper: return "Microsoft Visio"
    if "PROJECT" in upper: return "Microsoft Project"
    if "O365" in upper or "MICROSOFT 365" in upper: return "Microsoft 365 Apps"
    if "LTSC2024" in upper or "LTSC 2024" in upper: return "Office LTSC 2024"
    if "LTSC2021" in upper or "LTSC 2021" in upper: return "Office LTSC 2021"
    for year in (2024, 2021, 2019, 2016, 2013, 2010):
        if str(year) in upper: return f"Microsoft Office {year}"
    return "Microsoft Office"


def detect_office() -> List[Dict[str, Any]]:
    products: List[Dict[str, Any]] = []
    seen = set()
    for view, platform_name in ((winreg.KEY_WOW64_64KEY, "64-bit"), (winreg.KEY_WOW64_32KEY, "32-bit")):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Office\ClickToRun\Configuration", 0, winreg.KEY_READ | view) as key:
                ids = str(_value(key, "ProductReleaseIds", ""))
                for release_id in filter(None, re.split(r"[,;]", ids)):
                    identity = (release_id.strip().lower(), "c2r")
                    if identity in seen: continue
                    seen.add(identity)
                    products.append({
                        "product_name": _office_name(release_id), "release_id": release_id.strip(),
                        "version": _value(key, "VersionToReport", "Không xác định"), "build": _value(key, "VersionToReport", "Không xác định"),
                        "platform": _value(key, "Platform", platform_name), "install_type": "Click-to-Run",
                        "update_channel": _value(key, "UpdateChannel", _value(key, "CDNBaseUrl", "Không xác định")),
                        "installation_path": _value(key, "InstallationPath", "Không xác định"),
                        "shared_computer_licensing": _value(key, "SharedComputerLicensing", "Không xác định"),
                    })
        except OSError:
            pass
        uninstall = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall, 0, winreg.KEY_READ | view) as root:
                for i in range(winreg.QueryInfoKey(root)[0]):
                    try:
                        with winreg.OpenKey(root, winreg.EnumKey(root, i)) as key:
                            display = str(_value(key, "DisplayName", ""))
                            if not display or not any(x in display.lower() for x in ("microsoft office", "microsoft 365", "visio", "project")): continue
                            identity = (display.lower(), "msi")
                            if identity in seen: continue
                            seen.add(identity)
                            products.append({"product_name": _office_name(display), "release_id": display,
                                "version": _value(key, "DisplayVersion", "Không xác định"), "build": _value(key, "DisplayVersion", "Không xác định"),
                                "platform": platform_name, "install_type": "MSI", "update_channel": "Không áp dụng",
                                "installation_path": _value(key, "InstallLocation", "Không xác định"), "shared_computer_licensing": "Không áp dụng"})
                    except OSError: continue
        except OSError:
            pass
    return products

import hashlib
import logging
import re
import winreg

from core.hardware_collector import _wmi_rows
from core.license_models import DeviceIdentity

LOG = logging.getLogger(__name__)
INVALID = {"", "NONE", "UNKNOWN", "DEFAULT STRING", "TO BE FILLED BY O.E.M.", "SYSTEM SERIAL NUMBER",
           "00000000-0000-0000-0000-000000000000", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF", "KHÔNG XÁC ĐỊNH"}


def normalize_hardware_value(value):
    text = re.sub(r"\s+", " ", str(value or "").strip()).upper()
    if text in INVALID or not text.strip(" -0"):
        return ""
    return text


def build_device_identity(values):
    clean = {k: normalize_hardware_value(values.get(k)) for k in ("uuid", "bios", "board", "cpu", "manufacturer", "model", "machine_guid")}
    hardware = [clean[k] for k in ("uuid", "bios", "board", "cpu") if clean[k]]
    fallback = not hardware and bool(clean["machine_guid"])
    sources = hardware or [clean["machine_guid"]]
    if not sources:
        raise RuntimeError("Không thu thập được thông tin ổn định để tạo DEVICE_ID.")
    lines = ["PRODUCT=ATG_PC_AUDIT", "FEATURE=AGGREGATE"]
    for key in ("uuid", "bios", "board", "cpu"):
        if clean[key]: lines.append(f"{key.upper()}={clean[key]}")
    if fallback: lines.append(f"MACHINE_GUID={clean['machine_guid']}")
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest().upper()[:20]
    device_id = "ATG-PC-" + "-".join(digest[i:i+4] for i in range(0, 20, 4))
    confidence = "HIGH" if clean["uuid"] and any(clean[k] for k in ("bios", "board", "cpu")) else ("MEDIUM" if len(hardware) >= 2 else "LOW")
    return DeviceIdentity(device_id, confidence, len(sources), fallback)


def collect_device_identity():
    values = {}
    try:
        values["uuid"] = (_wmi_rows("Win32_ComputerSystemProduct", ["UUID"]) or [{}])[0].get("UUID")
        values["bios"] = (_wmi_rows("Win32_BIOS", ["SerialNumber"]) or [{}])[0].get("SerialNumber")
        values["board"] = (_wmi_rows("Win32_BaseBoard", ["SerialNumber"]) or [{}])[0].get("SerialNumber")
        values["cpu"] = (_wmi_rows("Win32_Processor", ["ProcessorId"]) or [{}])[0].get("ProcessorId")
    except Exception: LOG.warning("Không đọc đủ nguồn phần cứng tạo DEVICE_ID")
    try:
        row = (_wmi_rows("Win32_ComputerSystem", ["Manufacturer", "Model"]) or [{}])[0]
        values.update(manufacturer=row.get("Manufacturer"), model=row.get("Model"))
    except Exception: pass
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            values["machine_guid"] = winreg.QueryValueEx(key, "MachineGuid")[0]
    except OSError: pass
    identity = build_device_identity(values)
    LOG.info("DEVICE_ID generated: %s", identity.device_id[:15] + "-****-****-" + identity.device_id[-4:])
    return identity

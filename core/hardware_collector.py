import logging
import os
import platform
import socket
import uuid
import json
import subprocess
import ctypes
import winreg
from typing import Any, Dict, List

import psutil

LOG = logging.getLogger(__name__)


def _wmi_rows(class_name: str, fields: List[str]) -> List[Dict[str, Any]]:
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        service = win32com.client.GetObject(r"winmgmts:\\.\root\cimv2")
        query = f"SELECT {','.join(fields)} FROM {class_name}"
        return [{f: getattr(item, f, None) for f in fields} for item in service.ExecQuery(query)]
    except Exception as exc:
        LOG.exception("WMI lỗi tại %s", class_name)
        raise RuntimeError(f"Không đọc được {class_name}: {exc}") from exc
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def collect_computer() -> Dict[str, Any]:
    fields = ["Manufacturer", "Model", "SystemSKUNumber", "SystemType", "UserName", "Domain"]
    product_fields = ["IdentifyingNumber", "UUID"]
    try:
        system = (_wmi_rows("Win32_ComputerSystem", fields) or [{}])[0]
        product = (_wmi_rows("Win32_ComputerSystemProduct", product_fields) or [{}])[0]
    except RuntimeError:
        system, product = {}, {}
    return {
        "computer_name": socket.gethostname(),
        "windows_user": system.get("UserName") or os.environ.get("USERNAME", "Không xác định"),
        "manufacturer": system.get("Manufacturer") or "Không xác định",
        "model": system.get("Model") or "Không xác định",
        "system_sku": system.get("SystemSKUNumber") or "Không xác định",
        "serial_number": product.get("IdentifyingNumber") or "Không xác định",
        "uuid": product.get("UUID") or str(uuid.getnode()),
        "system_type": system.get("SystemType") or platform.machine(),
        "domain_workgroup": system.get("Domain") or "Không xác định",
    }


def collect_cpu() -> Dict[str, Any]:
    fields = ["Name", "Manufacturer", "NumberOfCores", "NumberOfLogicalProcessors", "MaxClockSpeed", "SocketDesignation", "AddressWidth"]
    try:
        rows = _wmi_rows("Win32_Processor", fields)
    except RuntimeError:
        rows = []
    first = rows[0] if rows else {}
    return {
        "name": first.get("Name") or platform.processor() or "Không xác định",
        "manufacturer": first.get("Manufacturer") or "Không xác định",
        "sockets": len(rows) or 1,
        "cores": sum(int(x.get("NumberOfCores") or 0) for x in rows) or psutil.cpu_count(logical=False),
        "threads": sum(int(x.get("NumberOfLogicalProcessors") or 0) for x in rows) or psutil.cpu_count(),
        "max_clock_mhz": first.get("MaxClockSpeed") or "Không xác định",
        "socket": first.get("SocketDesignation") or "Không xác định",
        "architecture": f"{first.get('AddressWidth') or (64 if platform.machine().endswith('64') else 32)}-bit",
    }


def collect_ram() -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    fields = ["DeviceLocator", "BankLabel", "Capacity", "Speed", "ConfiguredClockSpeed", "Manufacturer", "PartNumber", "SerialNumber", "SMBIOSMemoryType"]
    try:
        rows = _wmi_rows("Win32_PhysicalMemory", fields)
    except RuntimeError:
        rows = []
    modules = []
    for row in rows:
        modules.append({
            "slot": row.get("DeviceLocator") or "Không xác định",
            "bank": row.get("BankLabel") or "Không xác định",
            "capacity_gb": round(int(row.get("Capacity") or 0) / 1024**3, 2),
            "speed_mhz": row.get("Speed") or "Không xác định",
            "configured_clock_mhz": row.get("ConfiguredClockSpeed") or "Không xác định",
            "manufacturer": (row.get("Manufacturer") or "Không xác định").strip(),
            "part_number": (row.get("PartNumber") or "Không xác định").strip(),
            "serial_number": (row.get("SerialNumber") or "Không xác định").strip(),
            "smbios_type": row.get("SMBIOSMemoryType") or "Không xác định",
        })
    memory = psutil.virtual_memory()
    return {"total_gb": round(memory.total / 1024**3, 2), "module_count": len(modules)}, modules


def collect_bios() -> Dict[str, Any]:
    try:
        bios = (_wmi_rows("Win32_BIOS", ["SMBIOSBIOSVersion", "ReleaseDate", "Manufacturer", "SerialNumber"]) or [{}])[0]
        board = (_wmi_rows("Win32_BaseBoard", ["Manufacturer", "Product", "SerialNumber"]) or [{}])[0]
    except RuntimeError:
        bios, board = {}, {}
    return {
        "bios_version": bios.get("SMBIOSBIOSVersion") or "Không xác định",
        "bios_release_date": str(bios.get("ReleaseDate") or "Không xác định")[:8],
        "bios_manufacturer": bios.get("Manufacturer") or "Không xác định",
        "mainboard_manufacturer": board.get("Manufacturer") or "Không xác định",
        "mainboard_product": board.get("Product") or "Không xác định",
        "mainboard_serial": board.get("SerialNumber") or "Không xác định",
    }


def collect_gpu() -> List[Dict[str, Any]]:
    fields = ["Name", "VideoProcessor", "AdapterRAM", "DriverVersion", "DriverDate",
              "VideoModeDescription", "CurrentHorizontalResolution", "CurrentVerticalResolution",
              "Status", "Availability", "PNPDeviceID"]
    try:
        rows = _wmi_rows("Win32_VideoController", fields)
    except RuntimeError:
        rows = []
    result = []
    for index, row in enumerate(rows):
        width = int(row.get("CurrentHorizontalResolution") or 0)
        height = int(row.get("CurrentVerticalResolution") or 0)
        status = str(row.get("Status") or "Không xác định")
        ram = int(row.get("AdapterRAM") or 0)
        result.append({
            "gpu_index": index,
            "name": row.get("Name") or "Không xác định",
            "video_processor": row.get("VideoProcessor") or "Không xác định",
            "adapter_ram_gb": round(ram / 1024**3, 2) if ram else "Không xác định",
            "adapter_ram": ram,
            "driver_version": row.get("DriverVersion") or "Không xác định",
            "driver_date": str(row.get("DriverDate") or "Không xác định")[:8],
            "video_mode": row.get("VideoModeDescription") or (f"{width} x {height}" if width and height else "Không xác định"),
            "resolution": f"{width} x {height}" if width and height else "Không xác định",
            "status": status,
            "is_active": bool(width and height and status.upper() == "OK"),
            "pnp_device_id": row.get("PNPDeviceID") or "Không xác định",
        })
    return result


def _powershell_json(script: str):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=30, creationflags=flags,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "PowerShell không trả về dữ liệu")
    text = completed.stdout.strip()
    return json.loads(text) if text else []


def collect_disks() -> List[Dict[str, Any]]:
    script = r"""
$systemDisk = $null
try {$systemDisk = (Get-Partition -DriveLetter C -ErrorAction Stop | Select-Object -First 1).DiskNumber} catch {}
if ($null -eq $systemDisk) {
  try {
    $logical = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'" -ErrorAction Stop
    $partition = Get-CimAssociatedInstance -InputObject $logical -Association Win32_LogicalDiskToPartition -ErrorAction Stop | Select-Object -First 1
    if ($partition) {$systemDisk = $partition.DiskIndex}
  } catch {}
}
$rows = Get-CimInstance Win32_DiskDrive | ForEach-Object {
  $d = $_; $gd = Get-Disk -Number $d.Index -ErrorAction SilentlyContinue
  [pscustomobject]@{Index=$d.Index;Model=$d.Model;SerialNumber=$d.SerialNumber;
    BusType=if($gd){[string]$gd.BusType}else{$d.InterfaceType};
    MediaType=if($gd){[string]$gd.MediaType}else{$d.MediaType};
    PartitionStyle=if($gd){[string]$gd.PartitionStyle}else{'Unknown'};
    Size=$d.Size;Status=$d.Status;IsSystem=($d.Index -eq $systemDisk)}
}; @($rows) | ConvertTo-Json -Compress
"""
    try:
        rows = _powershell_json(script)
        if isinstance(rows, dict):
            rows = [rows]
    except Exception:
        LOG.exception("Không đọc được danh sách ổ đĩa")
        rows = []
    result = []
    for row in rows:
        media = str(row.get("MediaType") or "Không xác định")
        model = str(row.get("Model") or "")
        kind = "NVMe" if "nvme" in (model + str(row.get("BusType"))).lower() else ("SSD" if "ssd" in media.lower() or "ssd" in model.lower() else ("HDD" if "hdd" in media.lower() or "fixed hard disk" in media.lower() else "Không xác định"))
        result.append({
            "disk_index": row.get("Index"), "model": model or "Không xác định",
            "serial_number": str(row.get("SerialNumber") or "Không xác định").strip(),
            "bus_type": row.get("BusType") or "Không xác định", "media_type": media,
            "disk_type": kind, "partition_style": row.get("PartitionStyle") or "Không xác định",
            "capacity_gb": round(int(row.get("Size") or 0) / 1024**3, 2),
            "status": row.get("Status") or "Không xác định", "is_system": bool(row.get("IsSystem")),
        })
    return result


def collect_security() -> Dict[str, Any]:
    script = r"""
$t = $null; try {$t = Get-Tpm -ErrorAction Stop} catch {}
[pscustomobject]@{TpmPresent=if($t){$t.TpmPresent}else{$null};TpmEnabled=if($t){$t.TpmEnabled}else{$null};
 TpmReady=if($t){$t.TpmReady}else{$null};TpmSpecVersion=if($t){$t.SpecVersion}else{$null}} | ConvertTo-Json -Compress
"""
    try:
        row = _powershell_json(script)
    except Exception:
        LOG.exception("Không đọc được TPM/Secure Boot")
        row = {}
    firmware_mode = "Không xác định"
    try:
        firmware_type = ctypes.c_uint(0)
        if ctypes.windll.kernel32.GetFirmwareType(ctypes.byref(firmware_type)):
            firmware_mode = {1: "Legacy BIOS", 2: "UEFI"}.get(firmware_type.value, "Không xác định")
    except Exception:
        LOG.exception("Không xác định được Firmware Mode")
    secure_boot_enabled = None
    secure_boot_capable = None
    secure_boot_note = "Không đọc được trạng thái Secure Boot"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\SecureBoot\State") as key:
            secure_boot_enabled = bool(winreg.QueryValueEx(key, "UEFISecureBootEnabled")[0])
            secure_boot_capable = firmware_mode == "UEFI"
            secure_boot_note = "Đọc từ Registry SecureBoot State"
    except OSError:
        if firmware_mode != "UEFI":
            secure_boot_capable = False
            secure_boot_note = "Firmware không ở chế độ UEFI"
    return {
        "firmware_mode": firmware_mode,
        "secure_boot_capable": secure_boot_capable,
        "secure_boot_enabled": secure_boot_enabled,
        "secure_boot_note": secure_boot_note,
        "tpm_present": row.get("TpmPresent"), "tpm_enabled": row.get("TpmEnabled"),
        "tpm_ready": row.get("TpmReady"), "tpm_spec_version": row.get("TpmSpecVersion") or "Không xác định",
        "tpm_note": "Không đủ quyền kiểm tra TPM" if row.get("TpmPresent") is None else "Đọc bằng Get-Tpm",
    }

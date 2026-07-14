import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

LOG = logging.getLogger(__name__)

OFFICE_DIRS = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft Office",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft Office",
]


def _hidden_run(args, timeout=60):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def find_ospp() -> Optional[Path]:
    for base in OFFICE_DIRS:
        for version in ("Office16", "Office15", "Office14"):
            for path in (base / version / "OSPP.VBS", base / "root" / version / "OSPP.VBS"):
                if path.is_file(): return path
    return None


def find_vnextdiag() -> Optional[Path]:
    for base in OFFICE_DIRS:
        for path in (base / "Office16" / "vnextdiag.ps1", base / "root" / "Office16" / "vnextdiag.ps1"):
            if path.is_file(): return path
    return None


def normalize_office_status(value: str) -> str:
    text = value.upper()
    if "LICENSED" in text and "UNLICENSED" not in text: return "Đã kích hoạt"
    if "UNLICENSED" in text: return "Chưa kích hoạt"
    if "NOTIFICATIONS" in text or "NOTIFICATION" in text: return "Notification Mode"
    if "GRACE" in text or "TRIAL" in text: return "Đang trong thời gian Grace"
    if "EXPIRED" in text: return "Hết hạn"
    return "Không thể xác định"


def parse_ospp(output: str) -> List[Dict[str, Any]]:
    blocks = re.split(r"-{10,}", output)
    licenses = []
    labels = {
        "LICENSE NAME": "license_name", "LICENSE DESCRIPTION": "license_description",
        "LICENSE STATUS": "raw_status", "ERROR CODE": "error_code", "ERROR DESCRIPTION": "error_description",
        "Last 5 characters of installed product key": "last5", "REMAINING GRACE": "remaining_grace",
        "KMS machine name from DNS": "kms_machine", "KMS machine port": "kms_port",
    }
    for block in blocks:
        item: Dict[str, Any] = {}
        for line in block.splitlines():
            clean = line.strip().lstrip("> ")
            if ":" not in clean: continue
            key, value = clean.split(":", 1)
            for label, target in labels.items():
                if key.strip().upper() == label.upper(): item[target] = value.strip()
        if item.get("license_name") or item.get("raw_status"):
            item["product_name"] = item.get("license_name", "Microsoft Office")
            item["activation_status"] = normalize_office_status(item.get("raw_status", ""))
            item["partial_key"] = f"XXXXX-XXXXX-XXXXX-XXXXX-{item['last5'][-5:]}" if item.get("last5") else "Không có"
            item["mechanism"] = "OSPP.VBS (chỉ đọc /dstatusall)"
            licenses.append(item)
    return licenses


def check_office_licenses(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not products:
        return [{"product_name": "Microsoft Office", "activation_status": "Không có Office", "mechanism": "Không áp dụng", "partial_key": "Không có", "note": "Không phát hiện cài đặt Office."}]
    results: List[Dict[str, Any]] = []
    has_365 = any("365" in (p.get("product_name", "") + p.get("release_id", "")) for p in products)
    vnext = find_vnextdiag() if has_365 else None
    if has_365:
        if vnext:
            try:
                run = _hidden_run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(vnext), "-action", "list"])
                output = run.stdout
                state = next((line.split(":", 1)[1].strip() for line in output.splitlines() if "License State" in line and ":" in line), "")
                product = next((line.split(":", 1)[1].strip() for line in output.splitlines() if "Product Name" in line and ":" in line), "Microsoft 365 Apps")
                email = next((line.split(":", 1)[1].strip() for line in output.splitlines() if re.search(r"User Email|Email", line, re.I) and ":" in line), "")
                tenant = next((line.split(":", 1)[1].strip() for line in output.splitlines() if "Tenant" in line and ":" in line), "")
                results.append({"product_name": product, "activation_status": normalize_office_status(state), "raw_status": state or "Không xác định",
                    "mechanism": "LicensingNext / vnextdiag -action list", "partial_key": "Không áp dụng", "user_email": email,
                    "tenant_id": tenant, "sensitive_account_data": bool(email or tenant), "note": "Email/Tenant chỉ hiển thị cục bộ; mặc định không xuất file."})
            except Exception as exc:
                LOG.exception("Không chạy được vnextdiag ở chế độ list")
                results.append({"product_name": "Microsoft 365 Apps", "activation_status": "Không thể xác định", "mechanism": "LicensingNext", "partial_key": "Không áp dụng", "note": f"Không đọc được vnextdiag: {exc}"})
        else:
            results.append({"product_name": "Microsoft 365 Apps", "activation_status": "Không thể xác định", "mechanism": "LicensingNext", "partial_key": "Không áp dụng", "note": "Đã phát hiện Microsoft 365 Apps nhưng chưa thể xác nhận đầy đủ trạng thái kích hoạt vì không tìm thấy vnextdiag.ps1."})
    ospp = find_ospp()
    if ospp:
        try:
            run = _hidden_run(["cscript.exe", "//Nologo", str(ospp), "/dstatusall"])
            results.extend(parse_ospp(run.stdout))
        except Exception as exc:
            LOG.exception("Không chạy được OSPP /dstatusall")
            results.append({"product_name": "Office Volume/MSI", "activation_status": "Không thể xác định", "mechanism": "OSPP.VBS", "partial_key": "Không có", "note": str(exc)})
    elif not has_365:
        results.append({"product_name": "Microsoft Office", "activation_status": "Không thể xác định", "mechanism": "OSPP.VBS", "partial_key": "Không có", "note": "Không tìm thấy OSPP.VBS."})
    return results

import logging
import re
from typing import Any, Dict

LOG = logging.getLogger(__name__)
WINDOWS_APP_ID = "55c92734-d682-4d71-983e-d6ec3f16059f"
STATUS_MAP = {
    0: "Chưa có bản quyền", 1: "Đã kích hoạt", 2: "Đang trong thời gian OOB Grace",
    3: "Đang trong thời gian OOT Grace", 4: "Non-Genuine Grace",
    5: "Notification Mode", 6: "Extended Grace",
}


def mask_key(last5: Any) -> str:
    value = re.sub(r"[^A-Za-z0-9]", "", str(last5 or ""))[-5:].upper()
    return f"XXXXX-XXXXX-XXXXX-XXXXX-{value}" if value else "Không có"


def classify_channel(description: str, name: str = "") -> str:
    text = f"{description} {name}".upper()
    if "OEM_DM" in text or "OEM:DM" in text: return "OEM_DM"
    if "OEM_COA" in text or "OEM:COA" in text: return "OEM_COA"
    if "VOLUME_KMSCLIENT" in text or "VOLUME:GVLK" in text: return "Volume KMS Client"
    if "VOLUME_KMS" in text: return "Volume KMS Host"
    if "VOLUME_MAK" in text or "MAK" in text: return "Volume MAK"
    if "RETAIL" in text: return "Retail"
    if "EVAL" in text: return "Evaluation"
    return "Không xác định"


def collect_windows_license() -> Dict[str, Any]:
    result = {
        "edition": "Không xác định", "activation_status": "Không thể xác định",
        "license_channel": "Không xác định", "license_type": "Không xác định",
        "partial_key": "Không có", "oem_key_present": None, "oem_key_last5": "Không có",
        "permanent_activation": None, "expiration": "Không xác định", "grace_remaining_minutes": None,
        "license_status_reason": "Không xác định", "product_id": "Không xác định",
        "application_id": WINDOWS_APP_ID, "activation_id": "Không xác định", "technical_note": "",
    }
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        service = win32com.client.GetObject(r"winmgmts:\\.\root\cimv2")
        query = ("SELECT Name,Description,ApplicationID,ID,ProductKeyID,PartialProductKey,LicenseStatus,"
                 "LicenseStatusReason,GracePeriodRemaining,EvaluationEndDate,LicenseFamily "
                 "FROM SoftwareLicensingProduct WHERE ApplicationID='" + WINDOWS_APP_ID + "' AND PartialProductKey IS NOT NULL")
        products = list(service.ExecQuery(query))
        if products:
            products.sort(key=lambda x: (int(getattr(x, "LicenseStatus", 0) or 0) != 1, str(getattr(x, "Name", ""))))
            item = products[0]
            status = int(getattr(item, "LicenseStatus", -1) or 0)
            description = str(getattr(item, "Description", "") or "")
            name = str(getattr(item, "Name", "") or "")
            channel = classify_channel(description, name)
            grace = getattr(item, "GracePeriodRemaining", None)
            evaluation_end = str(getattr(item, "EvaluationEndDate", "") or "")
            expiration = "Không áp dụng / kích hoạt vĩnh viễn" if evaluation_end.startswith("1601") else (evaluation_end or "Không xác định")
            result.update({
                "edition": name or "Không xác định", "activation_status": STATUS_MAP.get(status, "Không xác định"),
                "license_channel": channel, "license_type": channel,
                "partial_key": mask_key(getattr(item, "PartialProductKey", None)),
                "grace_remaining_minutes": grace, "license_status_reason": str(getattr(item, "LicenseStatusReason", "Không xác định")),
                "product_id": str(getattr(item, "ProductKeyID", "Không xác định") or "Không xác định"),
                "activation_id": str(getattr(item, "ID", "Không xác định") or "Không xác định"),
                "expiration": expiration,
                "permanent_activation": status == 1 and int(grace or 0) == 0 and "KMS" not in channel,
                "technical_note": f"Nguồn chính: WMI SoftwareLicensingProduct; tìm thấy {len(products)} license Windows.",
            })
        else:
            result["activation_status"] = "Chưa có bản quyền"
            result["technical_note"] = "WMI không trả về sản phẩm Windows có PartialProductKey."
        services = list(service.ExecQuery("SELECT OA3xOriginalProductKey FROM SoftwareLicensingService"))
        if services:
            oem_key = str(getattr(services[0], "OA3xOriginalProductKey", "") or "")
            result["oem_key_present"] = bool(oem_key)
            result["oem_key_last5"] = mask_key(oem_key[-5:]) if oem_key else "Không có"
    except Exception as exc:
        LOG.exception("Không kiểm tra được bản quyền Windows")
        result["technical_note"] = f"Không đọc được WMI bản quyền: {exc}"
    finally:
        try: pythoncom.CoUninitialize()
        except Exception: pass
    return result

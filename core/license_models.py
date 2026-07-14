from dataclasses import asdict, dataclass
from enum import Enum
from typing import Optional


class LicenseStatus(str, Enum):
    VALID = "VALID"
    VALID_PERMANENT = "VALID_PERMANENT"
    VALID_OFFLINE_CACHE = "VALID_OFFLINE_CACHE"
    NOT_FOUND = "NOT_FOUND"
    EXPIRED = "EXPIRED"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    NETWORK_ERROR = "NETWORK_ERROR"
    SSL_ERROR = "SSL_ERROR"
    TIMEOUT = "TIMEOUT"
    DEVICE_ID_ERROR = "DEVICE_ID_ERROR"
    LICENSE_URL_NOT_CONFIGURED = "LICENSE_URL_NOT_CONFIGURED"
    CACHE_EXPIRED = "CACHE_EXPIRED"
    CLOCK_ROLLBACK_DETECTED = "CLOCK_ROLLBACK_DETECTED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class DeviceIdentity:
    device_id: str
    confidence: str
    source_count: int
    is_fallback: bool = False


@dataclass
class LicenseResult:
    status: LicenseStatus
    is_valid: bool = False
    device_id: str = ""
    company: str = ""
    license_name: str = ""
    feature_code: str = "AGGREGATE"
    expire_date: str = ""
    days_remaining: Optional[int] = None
    max_import_records: int = 0
    source: str = "NONE"
    message: str = ""
    checked_at: str = ""
    last_online_success_utc: str = ""

    def to_dict(self):
        data = asdict(self); data["status"] = self.status.value; return data

    @classmethod
    def from_dict(cls, data):
        values = dict(data); values["status"] = LicenseStatus(values["status"]); return cls(**values)


def mask_device_id(value: str) -> str:
    parts = value.split("-")
    return "-".join(parts[:3] + ["****", "****", parts[-1]]) if len(parts) == 7 else value

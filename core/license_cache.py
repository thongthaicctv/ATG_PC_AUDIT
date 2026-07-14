import json
import os
from datetime import datetime, timezone
from pathlib import Path

import win32crypt

from core.license_models import LicenseResult, LicenseStatus


class LicenseCache:
    def __init__(self, path=None): self.path = Path(path) if path else self._default_path()
    @staticmethod
    def _default_path():
        root = os.environ.get("PROGRAMDATA") or os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(root) / "ATG_PC_AUDIT" / "license" / "aggregate_license.dat"
    def save(self, result: LicenseResult, server_time=""):
        now = datetime.now(timezone.utc).isoformat()
        data = result.to_dict(); data.update(cache_version=1, last_online_success_utc=now,
            last_server_time_utc=server_time or now, last_app_run_utc=now)
        encrypted = win32crypt.CryptProtectData(json.dumps(data).encode("utf-8"), "ATG PC AUDIT", None, None, None, 0)
        self.path.parent.mkdir(parents=True, exist_ok=True); self.path.write_bytes(encrypted)
    def load(self, device_id, grace_days=30, now=None):
        now = now or datetime.now(timezone.utc)
        try:
            raw = win32crypt.CryptUnprotectData(self.path.read_bytes(), None, None, None, 0)[1]
            data = json.loads(raw.decode("utf-8")); last_run = datetime.fromisoformat(data["last_app_run_utc"])
            if now < last_run.replace(tzinfo=timezone.utc) - __import__("datetime").timedelta(minutes=10):
                return LicenseResult(LicenseStatus.CLOCK_ROLLBACK_DETECTED, device_id=device_id, message="Phát hiện thời gian hệ thống không hợp lệ.")
            online = datetime.fromisoformat(data["last_online_success_utc"]); online = online if online.tzinfo else online.replace(tzinfo=timezone.utc)
            if data.get("device_id", "").upper() != device_id.upper() or (now-online).days > int(grace_days): raise ValueError("cache expired")
            expiry = str(data.get("expire_date") or "").strip().upper()
            if expiry and expiry != "PERMANENT" and now.date() > datetime.strptime(expiry, "%Y-%m-%d").date(): raise ValueError("license expired")
            data["last_app_run_utc"] = now.isoformat()
            self.path.write_bytes(win32crypt.CryptProtectData(json.dumps(data).encode("utf-8"), "ATG PC AUDIT", None, None, None, 0))
            result = LicenseResult.from_dict({k:v for k,v in data.items() if k in LicenseResult.__dataclass_fields__})
            result.status=LicenseStatus.VALID_OFFLINE_CACHE;result.is_valid=True;result.source="OFFLINE_CACHE";result.message="Đang sử dụng license ngoại tuyến.";return result
        except Exception:
            return LicenseResult(LicenseStatus.CACHE_EXPIRED, device_id=device_id, message="Không có cache license ngoại tuyến hợp lệ.")
    def clear(self):
        try:self.path.unlink()
        except FileNotFoundError:pass

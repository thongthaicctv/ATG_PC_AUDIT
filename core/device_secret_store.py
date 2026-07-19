import os,secrets
from pathlib import Path
import win32crypt


def _security_root():
    roots=[os.environ.get("PROGRAMDATA"),os.environ.get("LOCALAPPDATA")]
    for root in roots:
        if root:
            path=Path(root)/"ATG_PC_AUDIT"/"security"
            try:path.mkdir(parents=True,exist_ok=True);return path
            except OSError:continue
    raise OSError("Không thể tạo thư mục bảo mật cục bộ.")


class DeviceSecretStore:
    def __init__(self,path=None):self.path=Path(path) if path else _security_root()/"device_secret.dat"
    def get_or_create(self):
        if self.path.exists():
            try:return win32crypt.CryptUnprotectData(self.path.read_bytes(),None,None,None,0)[1].decode("ascii")
            except Exception as exc:raise ValueError("Device secret cục bộ bị lỗi hoặc không thể giải mã.") from exc
        value=secrets.token_hex(32);encrypted=win32crypt.CryptProtectData(value.encode("ascii"),"ATG PC AUDIT device secret",None,None,None,0)
        self.path.parent.mkdir(parents=True,exist_ok=True);tmp=self.path.with_suffix(".tmp");tmp.write_bytes(encrypted);tmp.replace(self.path);return value


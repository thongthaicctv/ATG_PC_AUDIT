import json
import os
import re
import time
import logging
from datetime import datetime
from pathlib import Path

from core.auth.password_hasher import hash_password,verify_password as verify_encoded_password
LOG=logging.getLogger(__name__)


def _writable_path(relative: str) -> Path:
    candidates=[Path(os.environ.get("PROGRAMDATA",r"C:\ProgramData"))/"ATG_PC_AUDIT"/relative,Path(os.environ.get("LOCALAPPDATA",str(Path.home()/"AppData"/"Local")))/"ATG_PC_AUDIT"/relative]
    for path in candidates:
        try: path.parent.mkdir(parents=True,exist_ok=True); test=path.parent/".write_test"; test.write_text("ok"); test.unlink(); return path
        except OSError: continue
    raise OSError("Không thể tạo thư mục bảo mật trong ProgramData hoặc LocalAppData.")


def auth_path(base_dir=None): return Path(base_dir)/"admin_auth.json" if base_dir else _writable_path("security/admin_auth.json")


def validate_password(password):
    if len(password)<8: return False,"Mật khẩu phải có ít nhất 8 ký tự."
    if not re.search(r"[A-Za-zÀ-ỹ]",password): return False,"Mật khẩu phải có ít nhất một chữ."
    if not re.search(r"\d",password): return False,"Mật khẩu phải có ít nhất một số."
    return True,"Hợp lệ"


def set_password(password,base_dir=None):
    ok,msg=validate_password(password)
    if not ok: raise ValueError(msg)
    path=auth_path(base_dir);path.parent.mkdir(parents=True,exist_ok=True);now=datetime.now().isoformat(timespec="seconds")
    old={}
    if path.exists():
        try: old=json.loads(path.read_text(encoding="utf-8"))
        except Exception: old={}
    payload={"version":2,"algorithm":"pbkdf2_sha256","password_hash":hash_password(password),"username":old.get("username","administrator"),"display_name":old.get("display_name","Quản trị viên"),"role":"AGGREGATE_ADMIN","must_change_password":bool(old.get("must_change_password",False)),"created_at":old.get("created_at",now),"updated_at":now}
    tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");os.replace(tmp,path);return path


def verify_password(password,base_dir=None):
    path=auth_path(base_dir)
    if not path.exists(): return False
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        if data.get("password_hash"):return verify_encoded_password(password,data["password_hash"])
        import base64,hashlib,hmac
        salt=base64.b64decode(data["salt_base64"]);expected=base64.b64decode(data["password_hash_base64"]);actual=hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),salt,int(data["iterations"]));return hmac.compare_digest(actual,expected)
    except Exception: return False


def change_password(current,new,base_dir=None):
    if not verify_password(current,base_dir): raise ValueError("Mật khẩu hiện tại không đúng.")
    return set_password(new,base_dir)


class AdminSession:
    def __init__(self,max_attempts=5,lock_seconds=60,session_seconds=900):
        self.max_attempts=max_attempts; self.lock_seconds=lock_seconds; self.session_seconds=session_seconds; self.failures=0; self.locked_until=0.; self.last_activity=0.; self.authenticated=False
    def remaining_lock(self): return max(0,int(self.locked_until-time.time()+0.999))
    def login(self,password,base_dir=None):
        if self.remaining_lock(): return False,f"Đang khóa. Thử lại sau {self.remaining_lock()} giây."
        if verify_password(password,base_dir): self.failures=0; self.authenticated=True; self.touch(); LOG.info("Admin login successful"); return True,"Đăng nhập thành công."
        self.failures+=1;LOG.warning("Admin login failed")
        if self.failures>=self.max_attempts: self.locked_until=time.time()+self.lock_seconds; self.failures=0; return False,f"Đã nhập sai 5 lần. Khóa {self.lock_seconds} giây."
        return False,f"Mật khẩu không đúng. Còn {self.max_attempts-self.failures} lần thử."
    def touch(self): self.last_activity=time.time()
    def is_active(self):
        if not self.authenticated:return False
        if time.time()-self.last_activity>self.session_seconds:self.lock();return False
        return True
    def lock(self): self.authenticated=False; self.last_activity=0;LOG.info("Admin session locked")

import base64,json,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
import win32crypt

BACKOFF=(1,5,15,30,60)


def _outbox():
    for root in (os.environ.get("PROGRAMDATA"),os.environ.get("LOCALAPPDATA")):
        if root:
            p=Path(root)/"ATG_PC_AUDIT"/"outbox"
            try:p.mkdir(parents=True,exist_ok=True);return p
            except OSError:continue
    raise OSError("Không thể tạo hàng đợi ngoại tuyến.")


class SyncQueue:
    def __init__(self,path=None):self.path=Path(path) if path else _outbox();self.path.mkdir(parents=True,exist_ok=True)
    def _file(self,audit_id):return self.path/f"{audit_id}.queue"
    def put(self,payload,error_code="",error_message=""):
        audit_id=payload["audit_id"];old=self.metadata(audit_id) or {};now=datetime.now(timezone.utc);count=int(old.get("retry_count",0));delay=30 if error_code=="DEVICE_PENDING" else BACKOFF[min(count,len(BACKOFF)-1)]
        encrypted=win32crypt.CryptProtectData(json.dumps(payload,ensure_ascii=False,separators=(",",":")).encode("utf-8"),"ATG PC AUDIT queue",None,None,None,0)
        row={"audit_id":audit_id,"created_at":old.get("created_at") or now.isoformat(),"retry_count":count,"last_retry_at":old.get("last_retry_at",""),"next_retry_at":(now+timedelta(minutes=delay)).isoformat(),"last_error_code":error_code,"last_error_message":str(error_message)[:500],"encrypted_payload":base64.b64encode(encrypted).decode("ascii")}
        tmp=self._file(audit_id).with_suffix(".tmp");tmp.write_text(json.dumps(row,ensure_ascii=False),encoding="utf-8");tmp.replace(self._file(audit_id));return row
    def metadata(self,audit_id):
        try:return json.loads(self._file(audit_id).read_text(encoding="utf-8"))
        except Exception:return None
    def items(self,due_only=False):
        now=datetime.now(timezone.utc);out=[]
        for p in self.path.glob("*.queue"):
            try:
                row=json.loads(p.read_text(encoding="utf-8"));due=datetime.fromisoformat(row["next_retry_at"])
                if due_only and due>now:continue
                payload=json.loads(win32crypt.CryptUnprotectData(base64.b64decode(row["encrypted_payload"]),None,None,None,0)[1].decode("utf-8"));out.append((row,payload))
            except Exception:continue
        return out
    def mark_retry(self,row,payload,result):
        row["retry_count"]=int(row.get("retry_count",0))+1;row["last_retry_at"]=datetime.now(timezone.utc).isoformat();self.put(payload,result.code,result.message)
        stored=self.metadata(payload["audit_id"]);stored["retry_count"]=row["retry_count"];self._file(payload["audit_id"]).write_text(json.dumps(stored,ensure_ascii=False),encoding="utf-8")
    def remove(self,audit_id):self._file(audit_id).unlink(missing_ok=True)
    def count(self):return len(list(self.path.glob("*.queue")))


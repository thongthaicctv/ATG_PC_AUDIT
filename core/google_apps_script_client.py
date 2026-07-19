import json,ssl,urllib.error,urllib.request
from models.sync_models import ApiResult

RETRYABLE={"NETWORK_ERROR","TIMEOUT","SSL_ERROR","HTTP_5XX","SERVER_BUSY","DEVICE_PENDING","QUOTA_EXCEEDED"}


class GoogleAppsScriptClient:
    def __init__(self,url,timeout=20,max_response_mb=10):
        self.url=str(url or "").strip();self.timeout=int(timeout);self.max_bytes=int(max_response_mb)*1024*1024
        if self.url and (not self.url.startswith("https://") or not self.url.endswith("/exec")):raise ValueError("Web App URL phải là HTTPS và kết thúc bằng /exec.")
    def health_check(self):
        if not self.url:return ApiResult(False,"NOT_CONFIGURED","Chưa cấu hình Google Apps Script Web App URL.")
        try:
            with urllib.request.urlopen(self.url+"?action=HEALTH",timeout=self.timeout,context=ssl.create_default_context()) as r:return self._decode(r)
        except Exception as exc:return self._network_error(exc)
    def post(self,body):
        if not self.url:return ApiResult(False,"NOT_CONFIGURED","Chưa cấu hình Google Apps Script Web App URL.")
        req=urllib.request.Request(self.url,data=json.dumps(body,ensure_ascii=False).encode("utf-8"),headers={"Content-Type":"application/json; charset=utf-8","Accept":"application/json"},method="POST")
        try:
            with urllib.request.urlopen(req,timeout=self.timeout,context=ssl.create_default_context()) as r:return self._decode(r)
        except urllib.error.HTTPError as exc:
            if exc.code>=500:return ApiResult(False,"HTTP_5XX","Máy chủ Google tạm thời không sẵn sàng.",retryable=True,raw_status_code=exc.code)
            return ApiResult(False,"HTTP_ERROR",f"Máy chủ trả HTTP {exc.code}.",raw_status_code=exc.code)
        except Exception as exc:return self._network_error(exc)
    def _decode(self,response):
        content_type=str(response.headers.get("Content-Type","")).lower()
        data=response.read(self.max_bytes+1)
        if len(data)>self.max_bytes:return ApiResult(False,"RESPONSE_TOO_LARGE","Phản hồi máy chủ vượt giới hạn cho phép.")
        if "json" not in content_type:return ApiResult(False,"INVALID_RESPONSE","Máy chủ không trả dữ liệu JSON.",raw_status_code=response.status)
        try:obj=json.loads(data.decode("utf-8"))
        except Exception:return ApiResult(False,"INVALID_RESPONSE","Phản hồi JSON không hợp lệ.",raw_status_code=response.status)
        code=str(obj.get("code") or "UNKNOWN");return ApiResult(bool(obj.get("success")),code,str(obj.get("message") or ""),obj,code in RETRYABLE,str(obj.get("server_time") or ""),response.status)
    @staticmethod
    def _network_error(exc):
        code="TIMEOUT" if isinstance(exc,TimeoutError) else "SSL_ERROR" if isinstance(exc,ssl.SSLError) else "NETWORK_ERROR"
        message="Google Apps Script phản hồi quá thời gian chờ." if code=="TIMEOUT" else "Không thể kết nối Google Apps Script."
        return ApiResult(False,code,message,retryable=True)
    def submit_audit(self,auth,payload):return self.post({"action":"SUBMIT_AUDIT","auth":auth,"payload":payload})
    def check_submit_status(self,auth,audit_id):return self.post({"action":"CHECK_SUBMIT_STATUS","auth":auth,"audit_id":audit_id})
    def sync_summary(self,auth,last_change_seq):return self.post({"action":"SYNC_SUMMARY","auth":auth,"last_change_seq":last_change_seq})
    def sync_snapshot(self,auth,page=1,page_size=200):return self.post({"action":"SYNC_SNAPSHOT","auth":auth,"page":page,"page_size":page_size})
    def sync_changes(self,auth,after_change_seq,page_size=200):return self.post({"action":"SYNC_CHANGES","auth":auth,"after_change_seq":after_change_seq,"page_size":page_size})
    def get_audit_detail(self,auth,audit_id):return self.post({"action":"GET_AUDIT_DETAIL","auth":auth,"audit_id":audit_id})
    def list_conflicts(self,auth,**filters):return self.post({"action":"LIST_CONFLICTS","auth":auth,**filters})

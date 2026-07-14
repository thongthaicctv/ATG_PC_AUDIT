import json
import re
import socket
import ssl
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

from core.license_cache import LicenseCache
from core.license_models import LicenseResult, LicenseStatus
from core.resource_utils import resource_path

MAX_RESPONSE = 5 * 1024 * 1024


def _parse_gviz(text):
    start=text.find("{");end=text.rfind(")")
    if start<0 or end<=start:raise ValueError("Google Visualization response không hợp lệ")
    payload=json.loads(text[start:end]);table=payload.get("table",{});labels=[str(x.get("label") or x.get("id") or "").strip().lower() for x in table.get("cols",[])]
    aliases={"công ty":"company","ten cong ty":"company","device_id":"device_id","product_code":"product_code","feature_code":"feature_code","license_name":"license_name","status":"status","expire_date":"expire_date","max_import_records":"max_import_records","created_at":"created_at","updated_at":"updated_at","note":"note"}
    rows=[]
    for source in table.get("rows",[]):
        values=[]
        for cell in source.get("c",[]):
            value=None if cell is None else cell.get("v")
            match=re.fullmatch(r"Date\((\d{4}),(\d{1,2}),(\d{1,2})\)",str(value or ""))
            if match:
                year,month,day=map(int,match.groups());value=f"{year:04d}-{month+1:02d}-{day:02d}"
            values.append(value)
        rows.append({aliases.get(label,label):values[i] if i<len(values) else None for i,label in enumerate(labels)})
    return rows


def load_license_config():
    defaults={"api_url":"","product_code":"ATG_PC_AUDIT","feature_code":"AGGREGATE","request_timeout_seconds":15,"offline_grace_days":30,"refresh_hours":12}
    try: defaults.update(json.loads(resource_path("config/app_config.json").read_text(encoding="utf-8")).get("license",{}))
    except Exception: pass
    return defaults


class LicenseClient:
    def __init__(self, config=None, cache=None, opener=None): self.config=config or load_license_config();self.cache=cache or LicenseCache();self.opener=opener or urllib.request.urlopen
    def check(self, device_id, force_online=False):
        url=str(self.config.get("api_url") or "").strip()
        if not url or "DAN_LINK" in url:return LicenseResult(LicenseStatus.LICENSE_URL_NOT_CONFIGURED,device_id=device_id,message="Chưa cấu hình đường dẫn máy chủ cấp phép.")
        if not url.lower().startswith("https://"):return LicenseResult(LicenseStatus.INVALID_RESPONSE,device_id=device_id,message="Đường dẫn cấp phép phải sử dụng HTTPS.")
        try:
            separator="&" if "?" in url else "?";request_url=url+separator+"_atg_refresh="+str(int(datetime.now(timezone.utc).timestamp())) if force_online else url
            req=urllib.request.Request(request_url,headers={"User-Agent":"ATG-PC-AUDIT/1.0.0","Accept":"application/json","Cache-Control":"no-cache"})
            with self.opener(req,timeout=int(self.config.get("request_timeout_seconds",15))) as response:
                ctype=response.headers.get("Content-Type","").lower()
                if "json" not in ctype and "text/plain" not in ctype and not ("javascript" in ctype and "/gviz/" in url):raise ValueError("Content-Type không phải JSON")
                raw=response.read(MAX_RESPONSE+1)
                if len(raw)>MAX_RESPONSE:raise ValueError("Response vượt quá 5 MB")
                text=raw.decode("utf-8-sig");payload=_parse_gviz(text) if "/gviz/" in url else json.loads(text);server_time=payload.get("server_time","") if isinstance(payload,dict) else ""
                rows=payload.get("licenses",[]) if isinstance(payload,dict) else payload
                result=self._evaluate(rows,device_id)
                if result.is_valid:self.cache.save(result,server_time)
                elif result.status in (LicenseStatus.BLOCKED,LicenseStatus.REVOKED):self.cache.clear()
                return result
        except urllib.error.URLError as exc:
            reason=exc.reason
            status=LicenseStatus.SSL_ERROR if isinstance(reason,ssl.SSLError) else LicenseStatus.TIMEOUT if isinstance(reason,(TimeoutError,socket.timeout)) else LicenseStatus.NETWORK_ERROR
            cached=self.cache.load(device_id,int(self.config.get("offline_grace_days",30)))
            return cached if cached.is_valid else LicenseResult(status,device_id=device_id,message="Không thể kết nối máy chủ cấp phép.")
        except (TimeoutError,socket.timeout):
            cached=self.cache.load(device_id,int(self.config.get("offline_grace_days",30)));return cached if cached.is_valid else LicenseResult(LicenseStatus.TIMEOUT,device_id=device_id,message="Hết thời gian kiểm tra cấp phép.")
        except Exception as exc:return LicenseResult(LicenseStatus.INVALID_RESPONSE,device_id=device_id,message=f"Dữ liệu cấp phép không hợp lệ: {exc}")
    def _evaluate(self, rows, device_id):
        if not isinstance(rows,list):return LicenseResult(LicenseStatus.INVALID_RESPONSE,device_id=device_id,message="JSON license không chứa danh sách hợp lệ.")
        product=str(self.config.get("product_code","ATG_PC_AUDIT")).strip().upper();feature=str(self.config.get("feature_code","AGGREGATE")).strip().upper()
        matching=[r for r in rows if isinstance(r,dict) and str(r.get("device_id","")).strip().upper()==device_id.upper() and str(r.get("product_code","")).strip().upper()==product and str(r.get("feature_code","")).strip().upper()==feature]
        if not matching:return LicenseResult(LicenseStatus.NOT_FOUND,device_id=device_id,message="DEVICE_ID này chưa được cấp quyền.")
        row=matching[0];state=str(row.get("status","")).strip().upper()
        blocked={"BLOCKED":LicenseStatus.BLOCKED,"SUSPENDED":LicenseStatus.SUSPENDED,"REVOKED":LicenseStatus.REVOKED}
        if state in blocked:return LicenseResult(blocked[state],device_id=device_id,message=f"License có trạng thái {state}.")
        if state!="ACTIVE":return LicenseResult(LicenseStatus.INVALID_RESPONSE,device_id=device_id,message="Trạng thái license không hợp lệ.")
        expiry=str(row.get("expire_date") or "").strip().upper();days=None;status=LicenseStatus.VALID_PERMANENT
        if expiry not in ("","PERMANENT"):
            try: exp=datetime.strptime(expiry,"%Y-%m-%d").date()
            except ValueError:return LicenseResult(LicenseStatus.INVALID_RESPONSE,device_id=device_id,message="Ngày hết hạn không đúng yyyy-MM-dd.")
            days=(exp-date.today()).days
            if days<0:return LicenseResult(LicenseStatus.EXPIRED,device_id=device_id,expire_date=expiry,message=f"License đã hết hạn ngày {expiry}.")
            status=LicenseStatus.VALID
        try:limit=max(0,int(float(str(row.get("max_import_records") or "0").strip())))
        except ValueError:limit=0
        return LicenseResult(status,True,device_id,str(row.get("company") or ""),str(row.get("license_name") or ""),feature,expiry,days,limit,"ONLINE","Kích hoạt thành công",datetime.now(timezone.utc).isoformat())


class LicenseRequiredError(PermissionError): pass


def require_feature_license(result):
    if not result or not result.is_valid:raise LicenseRequiredError("Tính năng Tổng hợp yêu cầu license hợp lệ.")

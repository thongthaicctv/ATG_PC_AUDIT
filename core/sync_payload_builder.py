import hashlib,json,uuid
from copy import deepcopy
from core.profile_validator import validate_required_profile_fields

SCHEMA_VERSION="1.1"


def _json_safe(value):
    if isinstance(value,dict):return {str(k):_json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [_json_safe(v) for v in value]
    if isinstance(value,float) and value.is_integer():return int(value)
    if value is None or isinstance(value,(str,int,float,bool)):return value
    return str(value)


def canonical_json(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def payload_hash(payload):
    body=deepcopy(payload);body.pop("record_sha256",None)
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def build_sync_payload(result):
    d=result.to_dict() if hasattr(result,"to_dict") else deepcopy(result);m=d.get("metadata",{});validation=validate_required_profile_fields(m)
    if not validation["is_valid"]:raise ValueError("Thông tin hồ sơ chưa đầy đủ hoặc Mã nhân viên không hợp lệ.")
    m=validation["normalized_profile"];primary=next((x for x in d.get("network_adapters",[]) if x.get("interface_index")==d.get("primary_adapter_index")),{})
    disks=d.get("disks",[]) or []
    # Ổ hệ thống là ổ vật lý chứa phân vùng Windows C:, không phải dung lượng
    # riêng của phân vùng C: và cũng không chọn đại ổ đầu tiên trên máy nhiều ổ.
    system_drive=next((x for x in disks if x.get("is_system")),{})
    payload={"schema_version":SCHEMA_VERSION,"audit_id":d.get("audit_id") or str(uuid.uuid4()),"audit_time_iso":d.get("audited_at"),
      "profile":{"asset_code":m.get("asset_code","").upper(),"assigned_user":m.get("user") or m.get("assigned_user"),"employee_code":m.get("employee_code"),"department":m.get("department"),"location":m.get("location"),"auditor":m.get("auditor"),"audit_date":m.get("audit_date"),"note":m.get("notes") or m.get("note","")},
      "system":d.get("computer",{}),"cpu":d.get("cpu",{}),"ram_summary":d.get("ram_summary",{}),"ram_modules":d.get("ram_modules",[]),"system_drive":system_drive,"disks":disks,"gpus":d.get("gpu",[]),
      "windows":{**d.get("windows",{}),**d.get("security",{})},"windows11":{**d.get("windows11",{}),"recommendations":d.get("recommendations",[])},"windows_license":d.get("windows_license",{}),"office_licenses":d.get("office_licenses",[]),"network_adapters":d.get("network_adapters",[]),"network_plan":d.get("ip_plan",{}),"primary_adapter":primary}
    payload=_json_safe(payload);payload["record_sha256"]=payload_hash(payload);return payload

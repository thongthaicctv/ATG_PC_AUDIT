import csv
import ipaddress
import json
import re
import uuid
import logging
from pathlib import Path
from typing import Iterable,List

from core.csv_exporter import CSV_FIELDS,SCHEMA_VERSION,canonical_hash,unescape_excel_formula,FORMULA_FIELDS
from models.import_result import ImportPreview
from core.profile_validator import valid_employee_code

REQUIRED={"schema_version","export_id","audit_id","asset_code","computer_name","record_sha256"}
JSON_FIELDS={"ram_details_json","disks_details_json","gpu_details_json","network_adapters_json","windows_license_details_json","office_license_details_json","win11_checks_json"}
LOG=logging.getLogger(__name__)


def scan_csv_files(paths:Iterable[Path]):
    result=[]
    for p in paths:
        p=Path(p)
        if p.is_dir():result.extend(p.rglob("*.csv"))
        elif p.suffix.lower()==".csv":result.append(p)
    return sorted(set(x.resolve() for x in result))


def preview_files(paths,database=None)->List[ImportPreview]:
    previews=[]
    for path in scan_csv_files(paths):
        try:
            with path.open("r",encoding="utf-8-sig",newline="") as f:
                reader=csv.DictReader(f)
                if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
                    previews.append(ImportPreview(str(path),status="Thiếu cột",message="Thiếu: "+", ".join(sorted(REQUIRED-set(reader.fieldnames or [])))));continue
                rows=list(reader)
            for index,raw in enumerate(rows): previews.append(_validate(path,raw,database,"File chứa nhiều bản ghi. " if len(rows)>1 else ""))
        except UnicodeError as exc:previews.append(ImportPreview(str(path),status="CSV lỗi",message=f"Lỗi encoding: {exc}"))
        except Exception as exc:previews.append(ImportPreview(str(path),status="CSV lỗi",message=str(exc)))
    LOG.info("CSV preview completed: %s rows",len(previews));return previews


def _validate(path,raw,database,warning):
    hash_ok=canonical_hash(raw)==raw.get("record_sha256","")
    record=dict(raw)
    for key in FORMULA_FIELDS:record[key]=unescape_excel_formula(record.get(key,""))
    errors=[]
    schema=record.get("schema_version")
    if schema not in ("1.0",SCHEMA_VERSION):errors.append("Sai schema")
    if schema=="1.0" and not record.get("employee_code"):record["employee_code"]="";warning += "LEGACY_MISSING_EMPLOYEE_CODE; Bản ghi cũ chưa có Mã nhân viên. "
    if schema==SCHEMA_VERSION and not record.get("employee_code"):errors.append("Thiếu Mã nhân viên")
    if record.get("employee_code") and not valid_employee_code(record["employee_code"]):errors.append("Mã nhân viên không hợp lệ")
    if not record.get("asset_code") or not record.get("computer_name"):errors.append("Không đủ dữ liệu nhận dạng")
    if not any(record.get(x) for x in ("serial_number","uuid","asset_code")):errors.append("Không đủ dữ liệu nhận dạng")
    for key in JSON_FIELDS:
        try:json.loads(record.get(key) or "[]")
        except Exception:errors.append(f"JSON lỗi: {key}")
    for key in ("current_ipv4","planned_ipv4"):
        if record.get(key):
            try:ipaddress.ip_address(record[key])
            except ValueError:errors.append(f"IPv4 lỗi: {key}")
    if record.get("primary_mac") and not re.fullmatch(r"(?:[0-9A-Fa-f]{2}[-:]){5}[0-9A-Fa-f]{2}",record["primary_mac"]):errors.append("MAC không hợp lệ")
    for key in ("ram_total_gb","system_disk_size_gb","system_disk_free_gb"):
        if record.get(key):
            try:float(record[key])
            except ValueError:errors.append(f"Giá trị số lỗi: {key}")
    if errors:return ImportPreview(str(path),record,"; ".join(errors),"skip",warning+"; ".join(errors),hash_ok)
    if database and database.exists("audit_id",record["audit_id"]):return ImportPreview(str(path),record,"Lần kiểm tra đã tồn tại","skip",warning,hash_ok)
    if database and database.exists("export_id",record["export_id"]):return ImportPreview(str(path),record,"File xuất đã được import trước đó","skip",warning,hash_ok)
    matches=database.find_machine_matches(record) if database else []
    if len(matches)>1:return ImportPreview(str(path),record,"XUNG ĐỘT NHẬN DẠNG – CẦN QUẢN TRỊ XÁC NHẬN","skip",warning,hash_ok)
    status="Máy đã tồn tại – sẽ cập nhật" if matches else "Máy mới"
    if not hash_ok:status="Hash không khớp";warning += "Dữ liệu đã bị thay đổi hoặc không thể xác minh."
    return ImportPreview(str(path),record,status,"import",warning,hash_ok)


def import_previews(previews,database):
    items=[{"record":x.record,"file_path":x.file_path,"hash_verified":x.hash_verified,"warning":x.message,"action":x.action} for x in previews if x.action=="import"]
    return database.import_records(items,str(uuid.uuid4())) if items else 0

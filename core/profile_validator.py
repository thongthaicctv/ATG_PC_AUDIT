import logging,re

LOG=logging.getLogger(__name__)
EMPLOYEE_CODE_RE=re.compile(r"^[A-Z0-9._-]{2,30}$")
REQUIRED_FIELDS=(("asset_code","Loại máy tính"),("user","Người sử dụng"),("employee_code","Mã nhân viên"),("department","Phòng ban"),("location","Vị trí làm việc"),("auditor","Người thực hiện cập nhật"))


def normalize_employee_code(value):return str(value or "").strip().upper()


def valid_employee_code(value):return bool(EMPLOYEE_CODE_RE.fullmatch(normalize_employee_code(value)))


def validate_required_profile_fields(profile):
    LOG.info("Profile validation started");normalized={k:str(v or "").strip() for k,v in dict(profile or {}).items()};normalized["employee_code"]=normalize_employee_code(normalized.get("employee_code"));missing=[];invalid=[]
    for key,label in REQUIRED_FIELDS:
        if not normalized.get(key):missing.append(label)
    if normalized.get("employee_code") and not valid_employee_code(normalized["employee_code"]):invalid.append({"field":"Mã nhân viên","key":"employee_code","message":"Mã nhân viên chỉ được chứa chữ cái, số, dấu gạch ngang, gạch dưới hoặc dấu chấm; không được có khoảng trắng."})
    result={"is_valid":not missing and not invalid,"normalized_profile":normalized,"missing_fields":missing,"invalid_fields":invalid}
    if not result["is_valid"]:LOG.warning("Profile validation failed: missing=%s invalid=%s",missing,[x["field"] for x in invalid])
    return result

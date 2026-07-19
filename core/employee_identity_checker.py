from collections import defaultdict


def find_employee_identity_conflicts(records):
    groups=defaultdict(list)
    for row in records:
        code=str(row.get("employee_code") or "").strip().upper()
        if code:groups[code].append(row)
    conflicts=[]
    for code,items in groups.items():
        names={str(x.get("assigned_user") or "").strip().casefold() for x in items if str(x.get("assigned_user") or "").strip()}
        if len(names)>1:conflicts.append({"type":"EMPLOYEE_CODE_NAME_CONFLICT","employee_code":code,"assigned_users":sorted({str(x.get("assigned_user") or "") for x in items}),"departments":sorted({str(x.get("department") or "") for x in items}),"assets":sorted({str(x.get("asset_code") or "") for x in items})})
    return conflicts

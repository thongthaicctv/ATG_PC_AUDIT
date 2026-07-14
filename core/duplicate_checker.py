from collections import defaultdict


def find_duplicates(records):
    conflicts=[]
    for field,label in (("asset_code","Mã tài sản"),("serial_number","Serial"),("uuid","UUID"),("primary_mac","MAC vật lý"),("planned_ipv4","IP dự kiến")):
        groups=defaultdict(list)
        for r in records:
            value=str(r.get(field) or "").strip().lower()
            if value:groups[value].append(r)
        for value,items in groups.items():
            machine_ids={x.get("machine_id") for x in items}
            if len(machine_ids)>1:conflicts.append({"type":label,"value":value,"machines":", ".join(str(x.get("computer_name")) for x in items),"assets":", ".join(str(x.get("asset_code")) for x in items),"severity":"Đỏ","resolution":"Quản trị viên kiểm tra","status":"Chưa xử lý"})
    return conflicts

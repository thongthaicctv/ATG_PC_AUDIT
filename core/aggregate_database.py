import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from core.admin_auth import _writable_path


def database_path(base_dir=None): return Path(base_dir)/"atg_pc_audit_master.db" if base_dir else _writable_path("data/atg_pc_audit_master.db")


class AggregateDatabase:
    def __init__(self,path=None): self.path=Path(path) if path else database_path(); self.path.parent.mkdir(parents=True,exist_ok=True); self.initialize()
    @contextmanager
    def connect(self):
        con=sqlite3.connect(self.path,timeout=30); con.row_factory=sqlite3.Row; con.execute("PRAGMA foreign_keys=ON"); con.execute("PRAGMA journal_mode=WAL"); con.execute("PRAGMA synchronous=NORMAL")
        try: yield con
        finally: con.close()
    def initialize(self):
        script="""
CREATE TABLE IF NOT EXISTS schema_info(version INTEGER NOT NULL);
INSERT INTO schema_info(version) SELECT 1 WHERE NOT EXISTS(SELECT 1 FROM schema_info);
CREATE TABLE IF NOT EXISTS machines(id INTEGER PRIMARY KEY,asset_code TEXT,computer_name TEXT,serial_number TEXT,uuid TEXT,manufacturer TEXT,model TEXT,current_audit_id INTEGER,created_at TEXT,updated_at TEXT,is_active INTEGER DEFAULT 1,FOREIGN KEY(current_audit_id) REFERENCES audits(id));
CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY,audit_id TEXT UNIQUE,export_id TEXT UNIQUE,machine_id INTEGER NOT NULL,schema_version TEXT,app_version TEXT,audit_time_iso TEXT,imported_at TEXT,assigned_user TEXT,department TEXT,location TEXT,auditor TEXT,note TEXT,raw_csv_path TEXT,record_sha256 TEXT,hash_verified INTEGER,import_warning TEXT,full_record_json TEXT,FOREIGN KEY(machine_id) REFERENCES machines(id));
CREATE TABLE IF NOT EXISTS network_interfaces(id INTEGER PRIMARY KEY,audit_row_id INTEGER,adapter_name TEXT,adapter_type TEXT,physical_adapter INTEGER,mac_address TEXT,ipv4 TEXT,prefix_length TEXT,gateway TEXT,dns_servers TEXT,dhcp_enabled INTEGER,is_primary INTEGER,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS disks(id INTEGER PRIMARY KEY,audit_row_id INTEGER,disk_index INTEGER,model TEXT,serial_number TEXT,media_type TEXT,bus_type TEXT,partition_style TEXT,size_gb REAL,is_system_disk INTEGER,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS ram_modules(id INTEGER PRIMARY KEY,audit_row_id INTEGER,slot TEXT,bank TEXT,capacity_gb REAL,speed_mhz REAL,manufacturer TEXT,part_number TEXT,serial_number TEXT,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS windows_licenses(id INTEGER PRIMARY KEY,audit_row_id INTEGER,license_name TEXT,activation_status TEXT,license_type TEXT,license_channel TEXT,partial_key TEXT,expiration TEXT,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS office_licenses(id INTEGER PRIMARY KEY,audit_row_id INTEGER,product_name TEXT,version TEXT,activation_status TEXT,license_type TEXT,partial_key TEXT,expiration TEXT,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS import_history(id INTEGER PRIMARY KEY,import_batch_id TEXT,file_path TEXT,file_name TEXT,imported_at TEXT,result TEXT,message TEXT,audit_id TEXT,export_id TEXT);
CREATE TABLE IF NOT EXISTS admin_change_log(id INTEGER PRIMARY KEY,machine_id INTEGER,field_name TEXT,old_value TEXT,new_value TEXT,changed_by TEXT,changed_at TEXT,FOREIGN KEY(machine_id) REFERENCES machines(id));
CREATE INDEX IF NOT EXISTS idx_machine_asset ON machines(asset_code);CREATE INDEX IF NOT EXISTS idx_machine_name ON machines(computer_name);CREATE INDEX IF NOT EXISTS idx_machine_serial ON machines(serial_number);CREATE INDEX IF NOT EXISTS idx_machine_uuid ON machines(uuid);CREATE INDEX IF NOT EXISTS idx_audit_id ON audits(audit_id);CREATE INDEX IF NOT EXISTS idx_export_id ON audits(export_id);CREATE INDEX IF NOT EXISTS idx_audit_department ON audits(department);CREATE INDEX IF NOT EXISTS idx_audit_time ON audits(audit_time_iso);CREATE INDEX IF NOT EXISTS idx_network_mac ON network_interfaces(mac_address);CREATE INDEX IF NOT EXISTS idx_network_ipv4 ON network_interfaces(ipv4);
"""
        with self.connect() as con: con.executescript(script)
    def exists(self,column,value):
        if column not in ("audit_id","export_id"):return False
        with self.connect() as con:return con.execute(f"SELECT 1 FROM audits WHERE {column}=?",(value,)).fetchone() is not None
    def find_machine_matches(self,r):
        clauses=[];args=[]
        for col in ("asset_code","serial_number","uuid"):
            v=str(r.get(col) or "").strip()
            if v and v.lower() not in ("unknown","none","không xác định","to be filled by o.e.m.","default string","system serial number"):
                clauses.append(f"lower({col})=lower(?)");args.append(v)
        if not clauses:return []
        with self.connect() as con:return [dict(x) for x in con.execute("SELECT * FROM machines WHERE "+" OR ".join(clauses),args)]
    def import_records(self,items,batch_id):
        now=datetime.now().isoformat(timespec="seconds"); imported=0
        with self.connect() as con:
            con.execute("BEGIN")
            try:
                for item in items:
                    r=item["record"]; action=item.get("action","import")
                    if action=="skip":continue
                    if not r.get("asset_code") or not r.get("computer_name") or not r.get("audit_id") or not r.get("export_id"):raise ValueError("Bản ghi thiếu trường bắt buộc.")
                    matches=self.find_machine_matches_in_connection(con,r)
                    machine=matches[0] if len(matches)==1 else None
                    if not machine:
                        cur=con.execute("INSERT INTO machines(asset_code,computer_name,serial_number,uuid,manufacturer,model,created_at,updated_at,is_active) VALUES(?,?,?,?,?,?,?,?,1)",(r.get("asset_code"),r.get("computer_name"),r.get("serial_number"),r.get("uuid"),r.get("manufacturer"),r.get("model"),now,now)); machine_id=cur.lastrowid
                    else: machine_id=machine["id"]
                    cur=con.execute("INSERT INTO audits(audit_id,export_id,machine_id,schema_version,app_version,audit_time_iso,imported_at,assigned_user,department,location,auditor,note,raw_csv_path,record_sha256,hash_verified,import_warning,full_record_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(r["audit_id"],r["export_id"],machine_id,r.get("schema_version"),r.get("app_version"),r.get("audit_time_iso"),now,r.get("assigned_user"),r.get("department"),r.get("location"),r.get("auditor"),r.get("note"),item.get("file_path"),r.get("record_sha256"),int(item.get("hash_verified",False)),item.get("warning",""),json.dumps(r,ensure_ascii=False)))
                    audit_row=cur.lastrowid
                    self._details(con,audit_row,r)
                    old=con.execute("SELECT a.audit_time_iso FROM machines m LEFT JOIN audits a ON a.id=m.current_audit_id WHERE m.id=?",(machine_id,)).fetchone()
                    if not old or not old[0] or str(r.get("audit_time_iso",""))>=str(old[0]): con.execute("UPDATE machines SET current_audit_id=?,asset_code=?,computer_name=?,serial_number=?,uuid=?,manufacturer=?,model=?,updated_at=? WHERE id=?",(audit_row,r.get("asset_code"),r.get("computer_name"),r.get("serial_number"),r.get("uuid"),r.get("manufacturer"),r.get("model"),now,machine_id))
                    con.execute("INSERT INTO import_history(import_batch_id,file_path,file_name,imported_at,result,message,audit_id,export_id) VALUES(?,?,?,?,?,?,?,?)",(batch_id,item.get("file_path"),Path(item.get("file_path","")).name,now,"Imported",item.get("warning",""),r["audit_id"],r["export_id"])); imported+=1
                con.commit();return imported
            except Exception:con.rollback();raise
    def find_machine_matches_in_connection(self,con,r):
        clauses=[];args=[]
        for col in ("asset_code","serial_number","uuid"):
            v=str(r.get(col) or "").strip()
            if v and v.lower() not in ("unknown","none","không xác định","to be filled by o.e.m.","default string","system serial number"):clauses.append(f"lower({col})=lower(?)");args.append(v)
        return [dict(x) for x in con.execute("SELECT * FROM machines WHERE "+(" OR ".join(clauses) if clauses else "0"),args)]
    def _details(self,con,audit_id,r):
        def js(key):
            try:return json.loads(r.get(key) or "[]")
            except Exception:return []
        primary=r.get("primary_mac")
        for x in js("network_adapters_json"):con.execute("INSERT INTO network_interfaces(audit_row_id,adapter_name,adapter_type,physical_adapter,mac_address,ipv4,prefix_length,gateway,dns_servers,dhcp_enabled,is_primary) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(audit_id,x.get("name"),x.get("interface_type"),int(bool(x.get("physical_adapter"))),x.get("mac_address"),", ".join(x.get("ipv4",[])),", ".join(x.get("prefix_or_mask",[])),", ".join(x.get("default_gateway",[])),", ".join(x.get("dns_servers",[])),x.get("dhcp_enabled"),int(x.get("mac_address")==primary)))
        for x in js("disks_details_json"):con.execute("INSERT INTO disks(audit_row_id,disk_index,model,serial_number,media_type,bus_type,partition_style,size_gb,is_system_disk) VALUES(?,?,?,?,?,?,?,?,?)",(audit_id,x.get("disk_index"),x.get("model"),x.get("serial_number"),x.get("disk_type") or x.get("media_type"),x.get("bus_type"),x.get("partition_style"),x.get("capacity_gb"),int(bool(x.get("is_system")))))
        for x in js("ram_details_json"):con.execute("INSERT INTO ram_modules(audit_row_id,slot,bank,capacity_gb,speed_mhz,manufacturer,part_number,serial_number) VALUES(?,?,?,?,?,?,?,?)",(audit_id,x.get("slot"),x.get("bank"),x.get("capacity_gb"),x.get("speed_mhz"),x.get("manufacturer"),x.get("part_number"),x.get("serial_number")))
        con.execute("INSERT INTO windows_licenses(audit_row_id,license_name,activation_status,license_type,license_channel,partial_key,expiration) VALUES(?,?,?,?,?,?,?)",(audit_id,r.get("windows_license_name"),r.get("windows_activation_status"),r.get("windows_license_type"),r.get("windows_license_channel"),r.get("windows_partial_key"),r.get("windows_expiration")))
        for x in js("office_license_details_json"):con.execute("INSERT INTO office_licenses(audit_row_id,product_name,version,activation_status,license_type,partial_key,expiration) VALUES(?,?,?,?,?,?,?)",(audit_id,x.get("product_name"),x.get("version"),x.get("activation_status"),x.get("mechanism") or x.get("license_type"),x.get("partial_key"),x.get("expiration")))
    def current_records(self,search="",department="",user=""):
        sql="SELECT m.id machine_id,a.id audit_row_id,a.full_record_json,a.imported_at FROM machines m JOIN audits a ON a.id=m.current_audit_id WHERE m.is_active=1";args=[]
        if search:sql+=" AND (m.asset_code LIKE ? OR m.computer_name LIKE ? OR m.serial_number LIKE ? OR a.assigned_user LIKE ?)";args += [f"%{search}%"]*4
        if department:sql+=" AND a.department LIKE ?";args.append(f"%{department}%")
        if user:sql+=" AND a.assigned_user LIKE ?";args.append(f"%{user}%")
        with self.connect() as con:return [dict(json.loads(x["full_record_json"]),machine_id=x["machine_id"],audit_row_id=x["audit_row_id"],imported_at=x["imported_at"]) for x in con.execute(sql,args)]
    def stats(self):
        rows=self.current_records(); vals=lambda k:[str(x.get(k) or "") for x in rows]
        return {"total_machines":len(rows),"users":len(set(x for x in vals("assigned_user") if x)),"departments":len(set(x for x in vals("department") if x)),"win11_pass":sum("ĐỦ ĐIỀU KIỆN" in x and "KHÔNG" not in x for x in vals("win11_status")),"win11_fail":sum("KHÔNG ĐỦ" in x for x in vals("win11_status")),"win11_unknown":sum("CẦN KIỂM TRA" in x for x in vals("win11_status")),"windows_unlicensed":sum(x!="Đã kích hoạt" for x in vals("windows_activation_status")),"office_unlicensed":sum("Đã kích hoạt" not in x for x in vals("office_activation_summary")),"low_ram":sum(float(x.get("ram_total_gb") or 0)<8 for x in rows),"hdd":sum("HDD" in str(x.get("system_disk_media_type")) for x in rows)}
    def update_management(self,machine_id,audit_row_id,updates,changed_by="Quản trị viên"):
        now=datetime.now().isoformat(timespec="seconds")
        with self.connect() as con:
            row=con.execute("SELECT full_record_json FROM audits WHERE id=? AND machine_id=?",(audit_row_id,machine_id)).fetchone()
            if not row:raise ValueError("Không tìm thấy hồ sơ máy.")
            record=json.loads(row[0])
            for key,value in updates.items():
                old=str(record.get(key) or "")
                if old!=str(value):con.execute("INSERT INTO admin_change_log(machine_id,field_name,old_value,new_value,changed_by,changed_at) VALUES(?,?,?,?,?,?)",(machine_id,key,old,str(value),changed_by,now));record[key]=value
            con.execute("UPDATE audits SET assigned_user=?,department=?,location=?,note=?,full_record_json=? WHERE id=?",(record.get("assigned_user"),record.get("department"),record.get("location"),record.get("note"),json.dumps(record,ensure_ascii=False),audit_row_id))
            con.execute("UPDATE machines SET asset_code=?,updated_at=? WHERE id=?",(record.get("asset_code"),now,machine_id))

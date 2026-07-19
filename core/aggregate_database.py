import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from core.storage_path_manager import active_storage


def database_path(base_dir=None): return Path(base_dir)/"atg_pc_audit_master.db" if base_dir else active_storage().database_path


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
INSERT INTO schema_info(version) SELECT 12 WHERE NOT EXISTS(SELECT 1 FROM schema_info);
UPDATE schema_info SET version=12;
CREATE TABLE IF NOT EXISTS app_metadata(key TEXT PRIMARY KEY,value TEXT);
INSERT OR REPLACE INTO app_metadata(key,value) VALUES('application_id','ATG_PC_AUDIT');
INSERT OR REPLACE INTO app_metadata(key,value) VALUES('database_schema_version','12');
CREATE TABLE IF NOT EXISTS password_reset_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL,reset_at TEXT NOT NULL,windows_username TEXT,computer_name TEXT,reset_method TEXT NOT NULL,database_path TEXT,success INTEGER NOT NULL,note TEXT);
CREATE TABLE IF NOT EXISTS machines(id INTEGER PRIMARY KEY,asset_code TEXT,computer_name TEXT,serial_number TEXT,uuid TEXT,manufacturer TEXT,model TEXT,current_audit_id INTEGER,created_at TEXT,updated_at TEXT,is_active INTEGER DEFAULT 1,FOREIGN KEY(current_audit_id) REFERENCES audits(id));
CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY,audit_id TEXT UNIQUE,export_id TEXT UNIQUE,machine_id INTEGER NOT NULL,schema_version TEXT,app_version TEXT,audit_time_iso TEXT,imported_at TEXT,assigned_user TEXT,employee_code TEXT,department TEXT,location TEXT,auditor TEXT,note TEXT,raw_csv_path TEXT,record_sha256 TEXT,hash_verified INTEGER,import_warning TEXT,full_record_json TEXT,FOREIGN KEY(machine_id) REFERENCES machines(id));
CREATE TABLE IF NOT EXISTS employees(employee_code TEXT PRIMARY KEY,assigned_user TEXT,department TEXT,updated_at TEXT);
CREATE TABLE IF NOT EXISTS network_interfaces(id INTEGER PRIMARY KEY,audit_row_id INTEGER,adapter_name TEXT,adapter_type TEXT,physical_adapter INTEGER,mac_address TEXT,ipv4 TEXT,prefix_length TEXT,gateway TEXT,dns_servers TEXT,dhcp_enabled INTEGER,is_primary INTEGER,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS disks(id INTEGER PRIMARY KEY,audit_row_id INTEGER,disk_index INTEGER,model TEXT,serial_number TEXT,media_type TEXT,bus_type TEXT,partition_style TEXT,size_gb REAL,is_system_disk INTEGER,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS ram_modules(id INTEGER PRIMARY KEY,audit_row_id INTEGER,slot TEXT,bank TEXT,capacity_gb REAL,speed_mhz REAL,manufacturer TEXT,part_number TEXT,serial_number TEXT,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS windows_licenses(id INTEGER PRIMARY KEY,audit_row_id INTEGER,license_name TEXT,activation_status TEXT,license_type TEXT,license_channel TEXT,partial_key TEXT,expiration TEXT,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS office_licenses(id INTEGER PRIMARY KEY,audit_row_id INTEGER,product_name TEXT,version TEXT,activation_status TEXT,license_type TEXT,partial_key TEXT,expiration TEXT,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS import_history(id INTEGER PRIMARY KEY,import_batch_id TEXT,file_path TEXT,file_name TEXT,imported_at TEXT,result TEXT,message TEXT,audit_id TEXT,export_id TEXT);
CREATE TABLE IF NOT EXISTS admin_change_log(id INTEGER PRIMARY KEY,machine_id INTEGER,field_name TEXT,old_value TEXT,new_value TEXT,changed_by TEXT,changed_at TEXT,FOREIGN KEY(machine_id) REFERENCES machines(id));
CREATE TABLE IF NOT EXISTS machine_usage_history(id INTEGER PRIMARY KEY AUTOINCREMENT,machine_id INTEGER NOT NULL,sequence_no INTEGER NOT NULL,audit_row_id INTEGER,assigned_user TEXT,employee_code TEXT,department TEXT,location TEXT,started_at TEXT,ended_at TEXT,hardware_changes_json TEXT,hardware_snapshot_json TEXT,note TEXT,source TEXT,created_at TEXT NOT NULL,FOREIGN KEY(machine_id) REFERENCES machines(id),FOREIGN KEY(audit_row_id) REFERENCES audits(id));
CREATE TABLE IF NOT EXISTS sync_state(id INTEGER PRIMARY KEY CHECK(id=1),server_id TEXT,last_change_seq INTEGER DEFAULT 0,latest_change_seq INTEGER DEFAULT 0,last_sync_started_at TEXT,last_sync_completed_at TEXT,last_server_time TEXT,last_error_code TEXT,last_error_message TEXT);
INSERT OR IGNORE INTO sync_state(id,last_change_seq,latest_change_seq) VALUES(1,0,0);
CREATE TABLE IF NOT EXISTS sync_log(id INTEGER PRIMARY KEY,started_at TEXT,completed_at TEXT,result TEXT,from_change_seq INTEGER,to_change_seq INTEGER,record_count INTEGER,error_code TEXT,message TEXT);
CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY,conflict_id TEXT UNIQUE,conflict_type TEXT,asset_code TEXT,employee_code TEXT,audit_id TEXT,status TEXT,detected_at TEXT,details_json TEXT,last_change_seq INTEGER);
CREATE TABLE IF NOT EXISTS gpus(id INTEGER PRIMARY KEY,audit_row_id INTEGER,gpu_index INTEGER,name TEXT,driver_version TEXT,adapter_ram TEXT,status TEXT,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS win11_checks(id INTEGER PRIMARY KEY,audit_row_id INTEGER,check_name TEXT,actual TEXT,required TEXT,status TEXT,reason TEXT,FOREIGN KEY(audit_row_id) REFERENCES audits(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_machine_asset ON machines(asset_code);CREATE INDEX IF NOT EXISTS idx_machine_name ON machines(computer_name);CREATE INDEX IF NOT EXISTS idx_machine_serial ON machines(serial_number);CREATE INDEX IF NOT EXISTS idx_machine_uuid ON machines(uuid);CREATE INDEX IF NOT EXISTS idx_audit_id ON audits(audit_id);CREATE INDEX IF NOT EXISTS idx_export_id ON audits(export_id);CREATE INDEX IF NOT EXISTS idx_audit_department ON audits(department);CREATE INDEX IF NOT EXISTS idx_audit_time ON audits(audit_time_iso);CREATE INDEX IF NOT EXISTS idx_network_mac ON network_interfaces(mac_address);CREATE INDEX IF NOT EXISTS idx_network_ipv4 ON network_interfaces(ipv4);
CREATE INDEX IF NOT EXISTS idx_usage_machine_sequence ON machine_usage_history(machine_id,sequence_no);
"""
        with self.connect() as con:
            con.executescript(script)
            columns={row[1] for row in con.execute("PRAGMA table_info(audits)")}
            if "employee_code" not in columns: con.execute("ALTER TABLE audits ADD COLUMN employee_code TEXT")
            con.execute("CREATE INDEX IF NOT EXISTS idx_audit_employee_code ON audits(employee_code)")
            machine_columns={row[1] for row in con.execute("PRAGMA table_info(machines)")}
            for name,kind in (("employee_code","TEXT"),("assigned_user","TEXT"),("row_version","INTEGER DEFAULT 0"),("last_change_seq","INTEGER DEFAULT 0"),("status","TEXT DEFAULT 'ACTIVE'"),("detail_synced","INTEGER DEFAULT 1")):
                if name not in machine_columns:con.execute(f"ALTER TABLE machines ADD COLUMN {name} {kind}")
            sync_columns={row[1] for row in con.execute("PRAGMA table_info(sync_state)")}
            if "snapshot_completed" not in sync_columns:con.execute("ALTER TABLE sync_state ADD COLUMN snapshot_completed INTEGER DEFAULT 0")
            identity_version=con.execute("SELECT value FROM app_metadata WHERE key='identity_match_version'").fetchone()
            if not identity_version or identity_version[0]!="2":
                con.execute("UPDATE sync_state SET snapshot_completed=0")
                con.execute("INSERT OR REPLACE INTO app_metadata(key,value) VALUES('identity_match_version','2')")
            self._backfill_usage_history(con);con.commit()
    def exists(self,column,value):
        if column not in ("audit_id","export_id"):return False
        with self.connect() as con:return con.execute(f"SELECT 1 FROM audits WHERE {column}=?",(value,)).fetchone() is not None
    def find_machine_matches(self,r):
        for col in ("uuid","serial_number"):
            v=str(r.get(col) or "").strip()
            if v and v.lower() not in ("unknown","none","không xác định","to be filled by o.e.m.","default string","system serial number"):
                with self.connect() as con:rows=[dict(x) for x in con.execute(f"SELECT * FROM machines WHERE lower({col})=lower(?) ORDER BY is_active DESC,id",(v,))]
                if rows:return rows
        return []
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
                    machine=matches[0] if matches else None
                    if not machine:
                        cur=con.execute("INSERT INTO machines(asset_code,computer_name,serial_number,uuid,manufacturer,model,created_at,updated_at,is_active) VALUES(?,?,?,?,?,?,?,?,1)",(r.get("asset_code"),r.get("computer_name"),r.get("serial_number"),r.get("uuid"),r.get("manufacturer"),r.get("model"),now,now)); machine_id=cur.lastrowid
                    else: machine_id=machine["id"]
                    cur=con.execute("INSERT INTO audits(audit_id,export_id,machine_id,schema_version,app_version,audit_time_iso,imported_at,assigned_user,employee_code,department,location,auditor,note,raw_csv_path,record_sha256,hash_verified,import_warning,full_record_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(r["audit_id"],r["export_id"],machine_id,r.get("schema_version"),r.get("app_version"),r.get("audit_time_iso"),now,r.get("assigned_user"),r.get("employee_code"),r.get("department"),r.get("location"),r.get("auditor"),r.get("note"),item.get("file_path"),r.get("record_sha256"),int(item.get("hash_verified",False)),item.get("warning",""),json.dumps(r,ensure_ascii=False)))
                    if r.get("employee_code"): con.execute("INSERT INTO employees(employee_code,assigned_user,department,updated_at) VALUES(?,?,?,?) ON CONFLICT(employee_code) DO UPDATE SET assigned_user=excluded.assigned_user,department=excluded.department,updated_at=excluded.updated_at",(r.get("employee_code"),r.get("assigned_user"),r.get("department"),now))
                    audit_row=cur.lastrowid
                    self._details(con,audit_row,r)
                    old=con.execute("SELECT a.audit_time_iso FROM machines m LEFT JOIN audits a ON a.id=m.current_audit_id WHERE m.id=?",(machine_id,)).fetchone()
                    if not old or not old[0] or str(r.get("audit_time_iso",""))>=str(old[0]): con.execute("UPDATE machines SET current_audit_id=?,asset_code=?,computer_name=?,serial_number=?,uuid=?,manufacturer=?,model=?,updated_at=? WHERE id=?",(audit_row,r.get("asset_code"),r.get("computer_name"),r.get("serial_number"),r.get("uuid"),r.get("manufacturer"),r.get("model"),now,machine_id))
                    self._record_usage_history(con,machine_id,audit_row,r,"IMPORT")
                    con.execute("INSERT INTO import_history(import_batch_id,file_path,file_name,imported_at,result,message,audit_id,export_id) VALUES(?,?,?,?,?,?,?,?)",(batch_id,item.get("file_path"),Path(item.get("file_path","")).name,now,"Imported",item.get("warning",""),r["audit_id"],r["export_id"])); imported+=1
                con.commit();return imported
            except Exception:con.rollback();raise
    def find_machine_matches_in_connection(self,con,r):
        for col in ("uuid","serial_number"):
            v=str(r.get(col) or "").strip()
            if v and v.lower() not in ("unknown","none","không xác định","to be filled by o.e.m.","default string","system serial number"):
                rows=[dict(x) for x in con.execute(f"SELECT * FROM machines WHERE lower({col})=lower(?) ORDER BY is_active DESC,id",(v,))]
                if rows:return rows
        return []
    _HARDWARE_FIELDS=(("cpu_name","CPU"),("ram_total_gb","RAM"),("system_disk_model","Ổ đĩa"),("system_disk_size_gb","Dung lượng ổ"),("system_disk_media_type","Loại ổ"),("gpu_details_json","Card đồ họa"),("serial_number","Serial máy"),("model","Model"))
    def _hardware_snapshot(self,record):return {key:record.get(key) for key,_ in self._HARDWARE_FIELDS}
    def _record_usage_history(self,con,machine_id,audit_row_id,record,source="IMPORT"):
        now=datetime.now().isoformat(timespec="seconds");started=record.get("audit_time_iso") or record.get("audit_date") or now;snapshot=self._hardware_snapshot(record);last=con.execute("SELECT * FROM machine_usage_history WHERE machine_id=? ORDER BY sequence_no DESC LIMIT 1",(machine_id,)).fetchone();changes=[]
        if last:
            try:old=json.loads(last["hardware_snapshot_json"] or "{}")
            except Exception:old={}
            for key,label in self._HARDWARE_FIELDS:
                if str(old.get(key) or "")!=str(snapshot.get(key) or ""):changes.append({"field":key,"label":label,"old":old.get(key),"new":snapshot.get(key)})
            assignment_changed=any(str(last[key] or "")!=str(record.get(key) or "") for key in ("assigned_user","employee_code","department","location"))
            if not assignment_changed and not changes:return
            con.execute("UPDATE machine_usage_history SET ended_at=? WHERE id=? AND ended_at IS NULL",(started,last["id"]));sequence=int(last["sequence_no"])+1
        else:sequence=1
        note="Phần cứng thay đổi: "+"; ".join(f"{x['label']}: {x['old'] or '-'} → {x['new'] or '-'}" for x in changes) if changes else ("Ghi nhận người sử dụng đầu tiên" if sequence==1 else "Điều chuyển người sử dụng; phần cứng không thay đổi")
        con.execute("INSERT INTO machine_usage_history(machine_id,sequence_no,audit_row_id,assigned_user,employee_code,department,location,started_at,hardware_changes_json,hardware_snapshot_json,note,source,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(machine_id,sequence,audit_row_id,record.get("assigned_user"),record.get("employee_code"),record.get("department"),record.get("location"),started,json.dumps(changes,ensure_ascii=False),json.dumps(snapshot,ensure_ascii=False),note,source,now))
    def _backfill_usage_history(self,con):
        if con.execute("SELECT COUNT(*) FROM machine_usage_history").fetchone()[0]:return
        for audit in con.execute("SELECT id,machine_id,full_record_json FROM audits ORDER BY machine_id,audit_time_iso,id").fetchall():
            try:record=json.loads(audit["full_record_json"] or "{}")
            except Exception:continue
            self._record_usage_history(con,audit["machine_id"],audit["id"],record,"MIGRATION")
    def usage_history(self,machine_id):
        with self.connect() as con:
            machine=con.execute("SELECT uuid,serial_number FROM machines WHERE id=?",(machine_id,)).fetchone();ids=[machine_id]
            if machine:
                clauses=[];args=[]
                for column in ("uuid","serial_number"):
                    value=str(machine[column] or "").strip()
                    if value and value.lower() not in ("unknown","none","không xác định","default string","system serial number"):clauses.append(f"lower({column})=lower(?)");args.append(value)
                if clauses:ids=[x[0] for x in con.execute("SELECT id FROM machines WHERE "+" OR ".join(clauses),args)] or ids
            marks=",".join("?" for _ in ids);rows=[dict(x) for x in con.execute(f"SELECT * FROM machine_usage_history WHERE machine_id IN ({marks}) ORDER BY started_at,id",ids)]
        previous={}
        for index,row in enumerate(rows):
            try:snapshot=json.loads(row.get("hardware_snapshot_json") or "{}")
            except Exception:snapshot={}
            changes=[]
            if index:
                for key,label in self._HARDWARE_FIELDS:
                    if str(previous.get(key) or "")!=str(snapshot.get(key) or ""):changes.append(f"{label}: {previous.get(key) or '-'} → {snapshot.get(key) or '-'}")
            row["sequence_no"]=index+1;row["ended_at"]=rows[index+1].get("started_at") if index+1<len(rows) else None
            if changes:row["note"]="Phần cứng thay đổi: "+"; ".join(changes)
            elif index:row["note"]="Điều chuyển/nghiệm thu lần tiếp theo; phần cứng không thay đổi"
            previous=snapshot
        return rows
    def deactivate_machine(self,machine_id):
        with self.connect() as con:
            cur=con.execute("UPDATE machines SET is_active=0,updated_at=? WHERE id=? AND is_active=1",(datetime.now().isoformat(timespec="seconds"),machine_id));con.commit();return cur.rowcount
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
    def current_records(self,search="",department="",user="",employee_code=""):
        sql="SELECT m.id machine_id,a.id audit_row_id,a.full_record_json,a.imported_at FROM machines m JOIN audits a ON a.id=m.current_audit_id WHERE m.is_active=1";args=[]
        if search:sql+=" AND (m.asset_code LIKE ? OR m.computer_name LIKE ? OR m.serial_number LIKE ? OR a.assigned_user LIKE ? OR a.employee_code LIKE ?)";args += [f"%{search}%"]*5
        if department:sql+=" AND a.department LIKE ?";args.append(f"%{department}%")
        if user:sql+=" AND a.assigned_user LIKE ?";args.append(f"%{user}%")
        if employee_code:sql+=" AND a.employee_code LIKE ?";args.append(f"%{employee_code}%")
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
            con.execute("UPDATE audits SET assigned_user=?,employee_code=?,department=?,location=?,note=?,full_record_json=? WHERE id=?",(record.get("assigned_user"),record.get("employee_code"),record.get("department"),record.get("location"),record.get("note"),json.dumps(record,ensure_ascii=False),audit_row_id))
            con.execute("UPDATE machines SET asset_code=?,updated_at=? WHERE id=?",(record.get("asset_code"),now,machine_id))
            self._record_usage_history(con,machine_id,audit_row_id,record,"ADMIN_EDIT")
            con.commit()

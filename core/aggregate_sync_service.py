import json
from datetime import datetime


class AggregateSyncService:
    def __init__(self,database,client,auth_factory,page_size=200):self.db=database;self.client=client;self.auth_factory=auth_factory;self.page_size=page_size
    def state(self):
        with self.db.connect() as con:return dict(con.execute("SELECT * FROM sync_state WHERE id=1").fetchone())
    def sync(self,progress=None):
        started=datetime.now().isoformat(timespec="seconds");state=self.state();cursor=int(state.get("last_change_seq") or 0)
        with self.db.connect() as con:con.execute("UPDATE sync_state SET last_sync_started_at=?,last_error_code='',last_error_message='' WHERE id=1",(started,));con.commit()
        count=0
        if not int(state.get("snapshot_completed") or 0):
            page_number=1;snapshot_cursor=0
            while True:
                page=self.client.sync_snapshot(self.auth_factory(),page_number,self.page_size)
                if not page.success:self._error(started,cursor,page);return page
                records=page.data.get("records") or []
                with self.db.connect() as con:
                    con.execute("BEGIN IMMEDIATE")
                    for change in records:self._apply_change(con,change);count+=1
                    con.commit()
                snapshot_cursor=int(page.data.get("snapshot_change_seq") or snapshot_cursor)
                if progress:progress(len(records),int(page.data.get("total") or len(records)))
                if not page.data.get("has_more"):break
                page_number+=1
            cursor=snapshot_cursor
            with self.db.connect() as con:
                con.execute("UPDATE sync_state SET snapshot_completed=1,last_change_seq=?,latest_change_seq=? WHERE id=1",(cursor,cursor));con.commit()
        summary=self.client.sync_summary(self.auth_factory(),cursor)
        if not summary.success:self._error(started,cursor,summary);return summary
        latest=int(summary.data.get("latest_change_seq") or cursor)
        if summary.code=="UP_TO_DATE":self._complete(started,state.get("last_change_seq",0),cursor,count,summary);return summary
        try:
            while cursor<latest:
                page=self.client.sync_changes(self.auth_factory(),cursor,self.page_size)
                if not page.success:raise RuntimeError(f"{page.code}: {page.message}")
                records=page.data.get("records") or []
                with self.db.connect() as con:
                    con.execute("BEGIN IMMEDIATE")
                    for change in records:self._apply_change(con,change);count+=1
                    new_cursor=int(page.data.get("last_returned_seq") or cursor)
                    if new_cursor<=cursor and page.data.get("has_more"):raise RuntimeError("Cursor đồng bộ không tiến triển.")
                    con.execute("UPDATE sync_state SET last_change_seq=?,latest_change_seq=?,last_server_time=? WHERE id=1",(new_cursor,latest,page.server_time));con.commit();cursor=new_cursor
                if progress:progress(cursor,latest)
                if not page.data.get("has_more"):break
            self._complete(started,state.get("last_change_seq",0),cursor,count,summary);return summary
        except Exception as exc:
            with self.db.connect() as con:con.execute("UPDATE sync_state SET last_error_code='SYNC_FAILED',last_error_message=? WHERE id=1",(str(exc)[:500],));con.execute("INSERT INTO sync_log(started_at,completed_at,result,from_change_seq,to_change_seq,record_count,error_code,message) VALUES(?,?,?,?,?,?,?,?)",(started,datetime.now().isoformat(timespec="seconds"),"FAILED",state.get("last_change_seq",0),cursor,count,"SYNC_FAILED",str(exc)[:500]))
            raise
    def _apply_change(self,con,change):
        seq=int(change.get("change_seq") or 0);kind=change.get("change_type");raw=change.get("summary_json") or change.get("record") or {}
        if isinstance(raw,str):raw=json.loads(raw or "{}")
        aliases={"windows_name":"os_name","windows_edition":"os_edition","windows_display_version":"os_display_version","windows_build":"os_build","windows_architecture":"os_architecture","windows_activation":"windows_activation_status","office_product_summary":"office_product_summary","office_activation_summary":"office_activation_summary","audit_time":"audit_time_iso"}
        for source,target in aliases.items():
            if source in raw and target not in raw:raw[target]=raw[source]
        if kind=="CONFLICT_CREATED":
            con.execute("INSERT INTO conflicts(conflict_id,conflict_type,asset_code,employee_code,audit_id,status,detected_at,details_json,last_change_seq) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(conflict_id) DO UPDATE SET status=excluded.status,details_json=excluded.details_json,last_change_seq=excluded.last_change_seq",(change.get("entity_id"),raw.get("conflict_type"),change.get("asset_code"),change.get("employee_code"),change.get("audit_id"),raw.get("status","OPEN"),change.get("changed_at"),json.dumps(raw,ensure_ascii=False),seq));return
        asset=raw.get("asset_code") or change.get("asset_code")
        if not asset:return
        row=None
        for column,value in (("uuid",raw.get("uuid")),("serial_number",raw.get("serial_number"))):
            if value and str(value).strip().lower() not in ("unknown","none","không xác định","default string","system serial number"):
                row=con.execute(f"SELECT id FROM machines WHERE lower({column})=lower(?) ORDER BY is_active DESC,id LIMIT 1",(str(value).strip(),)).fetchone()
                if row:break
        now=datetime.now().isoformat(timespec="seconds")
        if row:
            machine_id=row[0];con.execute("UPDATE machines SET asset_code=?,computer_name=?,serial_number=?,uuid=?,manufacturer=?,model=?,employee_code=?,assigned_user=?,row_version=?,last_change_seq=?,status=?,updated_at=?,is_active=1 WHERE id=?",(asset,raw.get("computer_name"),raw.get("serial_number"),raw.get("uuid"),raw.get("manufacturer"),raw.get("model"),raw.get("employee_code"),raw.get("assigned_user"),raw.get("row_version",0),seq,raw.get("status","ACTIVE"),now,machine_id))
        else:
            cur=con.execute("INSERT INTO machines(asset_code,computer_name,serial_number,uuid,manufacturer,model,employee_code,assigned_user,row_version,last_change_seq,status,created_at,updated_at,is_active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)",(asset,raw.get("computer_name"),raw.get("serial_number"),raw.get("uuid"),raw.get("manufacturer"),raw.get("model"),raw.get("employee_code"),raw.get("assigned_user"),raw.get("row_version",0),seq,raw.get("status","ACTIVE"),now,now));machine_id=cur.lastrowid
        audit_id=raw.get("current_audit_id") or change.get("audit_id")
        if audit_id:
            audit=con.execute("SELECT id FROM audits WHERE audit_id=?",(audit_id,)).fetchone()
            if not audit:
                cur=con.execute("INSERT INTO audits(audit_id,export_id,machine_id,schema_version,app_version,audit_time_iso,imported_at,assigned_user,employee_code,department,location,auditor,note,record_sha256,hash_verified,import_warning,full_record_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(audit_id,"SYNC-"+str(audit_id),machine_id,"1.1","1.0.0",raw.get("audit_time"),now,raw.get("assigned_user"),raw.get("employee_code"),raw.get("department"),raw.get("location"),raw.get("auditor"),"",raw.get("record_sha256"),1,"SYNC_SUMMARY",json.dumps(raw,ensure_ascii=False)));audit_row=cur.lastrowid
            else:audit_row=audit[0];con.execute("UPDATE audits SET full_record_json=?,assigned_user=?,employee_code=?,department=?,location=? WHERE id=?",(json.dumps(raw,ensure_ascii=False),raw.get("assigned_user"),raw.get("employee_code"),raw.get("department"),raw.get("location"),audit_row))
            con.execute("UPDATE machines SET current_audit_id=?,detail_synced=0 WHERE id=?",(audit_row,machine_id))
            self.db._record_usage_history(con,machine_id,audit_row,raw,"SYNC")
        if raw.get("employee_code"):con.execute("INSERT INTO employees(employee_code,assigned_user,department,updated_at) VALUES(?,?,?,?) ON CONFLICT(employee_code) DO UPDATE SET assigned_user=excluded.assigned_user,department=excluded.department,updated_at=excluded.updated_at",(raw.get("employee_code"),raw.get("assigned_user"),raw.get("department"),now))
    def _complete(self,started,old,cursor,count,result):
        done=datetime.now().isoformat(timespec="seconds")
        with self.db.connect() as con:con.execute("UPDATE sync_state SET last_sync_completed_at=?,latest_change_seq=?,last_server_time=?,last_error_code='',last_error_message='' WHERE id=1",(done,int(result.data.get("latest_change_seq") or cursor),result.server_time));con.execute("INSERT INTO sync_log(started_at,completed_at,result,from_change_seq,to_change_seq,record_count,message) VALUES(?,?,?,?,?,?,?)",(started,done,"SUCCESS",old,cursor,count,result.message));con.commit()
    def _error(self,started,cursor,result):
        with self.db.connect() as con:con.execute("UPDATE sync_state SET last_error_code=?,last_error_message=? WHERE id=1",(result.code,result.message));con.execute("INSERT INTO sync_log(started_at,completed_at,result,from_change_seq,to_change_seq,record_count,error_code,message) VALUES(?,?,?,?,?,?,?,?)",(started,datetime.now().isoformat(timespec="seconds"),"FAILED",cursor,cursor,0,result.code,result.message));con.commit()

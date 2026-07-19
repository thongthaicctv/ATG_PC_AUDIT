import tempfile,unittest
from pathlib import Path
from core.aggregate_database import AggregateDatabase

class DatabaseTests(unittest.TestCase):
    def test_create_schema_and_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AggregateDatabase(Path(tmp)/"db.sqlite")
            with db.connect() as con:
                names={x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")};self.assertTrue({"machines","audits","network_interfaces","import_history","admin_change_log"}.issubset(names))
            with self.assertRaises(Exception):db.import_records([{"record":{"audit_id":"a","export_id":"e"},"action":"import"}],"b")
            with db.connect() as con:self.assertEqual(con.execute("SELECT count(*) FROM machines").fetchone()[0],0)

    def test_database_pragmas(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AggregateDatabase(Path(tmp)/"db.sqlite")
            with db.connect() as con:self.assertEqual(con.execute("PRAGMA foreign_keys").fetchone()[0],1);self.assertEqual(con.execute("PRAGMA journal_mode").fetchone()[0].lower(),"wal")

    def test_schema_version_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AggregateDatabase(Path(tmp)/"db.sqlite")
            with db.connect() as con:self.assertEqual(con.execute("SELECT version FROM schema_info").fetchone()[0],12)

    def test_transfer_history_hardware_changes_and_delete_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AggregateDatabase(Path(tmp)/"db.sqlite")
            def record(audit,asset,user,employee,ram):return {"audit_id":audit,"export_id":"e-"+audit,"asset_code":asset,"computer_name":"PC-01","serial_number":"SERIAL-01","uuid":"UUID-01","assigned_user":user,"employee_code":employee,"department":"HCNS","location":"T2","audit_time_iso":"2026-07-1"+("0" if audit=="a1" else "8")+"T08:00:00","cpu_name":"Intel","ram_total_gb":ram,"system_disk_model":"SSD","system_disk_size_gb":512,"network_adapters_json":"[]","disks_details_json":"[]","ram_details_json":"[]","office_license_details_json":"[]"}
            db.import_records([{"record":record("a1","LAPTOP","Nhân viên A","NV01",8)}],"b1")
            db.import_records([{"record":record("a2","LAPTOP2","Nhân viên B","NV02",16)}],"b2")
            rows=db.current_records();self.assertEqual(len(rows),1);history=db.usage_history(rows[0]["machine_id"]);self.assertEqual([x["sequence_no"] for x in history],[1,2]);self.assertIn("RAM",history[1]["note"]);self.assertEqual(history[0]["ended_at"],"2026-07-18T08:00:00")
            self.assertEqual(db.deactivate_machine(rows[0]["machine_id"]),1);self.assertEqual(db.current_records(),[])

    def test_same_machine_type_does_not_merge_different_hardware(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AggregateDatabase(Path(tmp)/"db.sqlite")
            def record(audit,serial,uuid,name):return {"audit_id":audit,"export_id":"e-"+audit,"asset_code":"BỘ PC","computer_name":name,"serial_number":serial,"uuid":uuid,"audit_time_iso":"2026-07-18T08:00:00","network_adapters_json":"[]","disks_details_json":"[]","ram_details_json":"[]","office_license_details_json":"[]"}
            db.import_records([{"record":record("a1","SER-01","UUID-01","PC-01")},{"record":record("a2","SER-02","UUID-02","PC-02")}],"batch")
            self.assertEqual(len(db.current_records()),2)

if __name__=="__main__":unittest.main()

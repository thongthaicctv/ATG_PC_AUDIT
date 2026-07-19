import tempfile,unittest
from pathlib import Path
from core.aggregate_database import AggregateDatabase
from core.aggregate_sync_service import AggregateSyncService
from models.sync_models import ApiResult


class FakeClient:
    def sync_snapshot(self,auth,page,page_size):return ApiResult(True,"SYNC_SNAPSHOT","OK",{"snapshot_change_seq":0,"total":0,"has_more":False,"records":[]})
    def sync_summary(self,auth,last):return ApiResult(True,"SYNC_AVAILABLE","Có dữ liệu",{"latest_change_seq":1},server_time="2026-07-17T00:00:00Z")
    def sync_changes(self,auth,after,page_size):
        summary={"asset_code":"PC01","computer_name":"MAY01","assigned_user":"Nguyễn A","employee_code":"NV01","department":"IT","current_audit_id":"AUDIT01","row_version":1,"windows_edition":"Windows 11","status":"ACTIVE"}
        return ApiResult(True,"SYNC_PAGE","OK",{"last_returned_seq":1,"latest_change_seq":1,"has_more":False,"records":[{"change_seq":1,"change_type":"MACHINE_INSERT","audit_id":"AUDIT01","asset_code":"PC01","summary_json":summary}]})


class AggregateSyncTests(unittest.TestCase):
    def test_sync_upserts_machine_audit_employee_and_cursor(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AggregateDatabase(Path(tmp)/"db.sqlite");AggregateSyncService(db,FakeClient(),lambda:{}).sync()
            rows=db.current_records();self.assertEqual(rows[0]["asset_code"],"PC01");self.assertEqual(rows[0]["employee_code"],"NV01");self.assertEqual(AggregateSyncService(db,FakeClient(),lambda:{}).state()["last_change_seq"],1)

    def test_first_sync_imports_current_snapshot_without_change_log(self):
        class SnapshotClient(FakeClient):
            def sync_snapshot(self,auth,page,page_size):
                row={"asset_code":"PC-SNAPSHOT","computer_name":"MAY-CU","serial_number":"SER-OLD","current_audit_id":"AUD-OLD","assigned_user":"Nhan vien cu"}
                return ApiResult(True,"SYNC_SNAPSHOT","OK",{"snapshot_change_seq":6,"total":1,"has_more":False,"records":[{"change_seq":6,"change_type":"MACHINE_SNAPSHOT","asset_code":"PC-SNAPSHOT","summary_json":row}]})
            def sync_summary(self,auth,last):return ApiResult(True,"UP_TO_DATE","OK",{"latest_change_seq":6})
        with tempfile.TemporaryDirectory() as tmp:
            db=AggregateDatabase(Path(tmp)/"db.sqlite");AggregateSyncService(db,SnapshotClient(),lambda:{}).sync()
            self.assertEqual([x["asset_code"] for x in db.current_records()],["PC-SNAPSHOT"])
            self.assertEqual(AggregateSyncService(db,SnapshotClient(),lambda:{}).state()["last_change_seq"],6)


if __name__=="__main__":unittest.main()

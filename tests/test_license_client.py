import io,json,unittest,urllib.error
from datetime import date,timedelta
from core.license_client import LicenseClient,_parse_gviz
from core.license_models import LicenseStatus


class Response(io.BytesIO):
    def __init__(self,data):super().__init__(json.dumps(data).encode());self.headers={"Content-Type":"application/json"}
    def __enter__(self):return self
    def __exit__(self,*args):pass


class DummyCache:
    def save(self,*args):pass
    def clear(self):pass

class OfflineCache(DummyCache):
    def load(self,device_id,grace_days):
        from core.license_models import LicenseResult
        return LicenseResult(LicenseStatus.VALID_OFFLINE_CACHE,True,device_id,source="OFFLINE_CACHE",message="Đang sử dụng license ngoại tuyến.")


class LicenseClientTests(unittest.TestCase):
    def client(self,rows):return LicenseClient({"api_url":"https://example.test","product_code":"ATG_PC_AUDIT","feature_code":"AGGREGATE"},DummyCache(),lambda *a,**k:Response(rows))
    def row(self,**kw):
        row={"device_id":"ATG-PC-AAAA-BBBB-CCCC-DDDD-EEEE","product_code":"ATG_PC_AUDIT","feature_code":"AGGREGATE","status":"ACTIVE","expire_date":"PERMANENT"};row.update(kw);return row
    def test_permanent_and_list(self):self.assertEqual(self.client([self.row()]).check(self.row()["device_id"]).status,LicenseStatus.VALID_PERMANENT)
    def test_not_found_product_feature_and_blocked(self):
        did=self.row()["device_id"];self.assertEqual(self.client([]).check(did).status,LicenseStatus.NOT_FOUND);self.assertEqual(self.client([self.row(product_code="X")]).check(did).status,LicenseStatus.NOT_FOUND);self.assertEqual(self.client([self.row(status="BLOCKED")]).check(did).status,LicenseStatus.BLOCKED)
    def test_expired_and_future(self):
        did=self.row()["device_id"];past=(date.today()-timedelta(days=1)).isoformat();future=(date.today()+timedelta(days=1)).isoformat();self.assertEqual(self.client([self.row(expire_date=past)]).check(did).status,LicenseStatus.EXPIRED);self.assertTrue(self.client([self.row(expire_date=future)]).check(did).is_valid)
    def test_root_object_and_bad_date(self):
        did=self.row()["device_id"];self.assertTrue(self.client({"success":True,"licenses":[self.row()]}).check(did).is_valid);self.assertEqual(self.client([self.row(expire_date="14/07/2027")]).check(did).status,LicenseStatus.INVALID_RESPONSE)
    def test_google_visualization_parser(self):
        body='google.visualization.Query.setResponse({"table":{"cols":[{"label":"device_id"},{"label":"status"},{"label":"expire_date"}],"rows":[{"c":[{"v":"D1"},{"v":"ACTIVE"},{"v":"Date(2027,11,31)"}]}]}});'
        self.assertEqual(_parse_gviz(body),[{"device_id":"D1","status":"ACTIVE","expire_date":"2027-12-31"}])
    def test_google_numeric_record_limit(self):
        did=self.row()["device_id"];result=self.client([self.row(max_import_records=9999.0)]).check(did);self.assertEqual(result.max_import_records,9999)
    def test_network_failure_uses_valid_offline_cache(self):
        def offline(*args,**kwargs):raise urllib.error.URLError("offline")
        client=LicenseClient({"api_url":"https://example.test","offline_grace_days":30},OfflineCache(),offline)
        result=client.check(self.row()["device_id"]);self.assertTrue(result.is_valid);self.assertEqual(result.source,"OFFLINE_CACHE")

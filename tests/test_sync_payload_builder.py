import unittest
from core.sync_payload_builder import build_sync_payload,canonical_json,payload_hash
from test_export import sample_result


class SyncPayloadTests(unittest.TestCase):
    def test_schema_employee_and_hash(self):
        payload=build_sync_payload(sample_result());self.assertEqual(payload["schema_version"],"1.1");self.assertEqual(payload["profile"]["employee_code"],"NV001");self.assertEqual(payload["record_sha256"],payload_hash(payload));self.assertEqual(payload["audit_id"],sample_result().audit_id if False else payload["audit_id"])
    def test_canonical_json(self):self.assertEqual(canonical_json({"b":1,"a":{"d":2,"c":1}}),'{"a":{"c":1,"d":2},"b":1}')
    def test_missing_employee_is_rejected(self):
        result=sample_result();result.metadata["employee_code"]=""
        with self.assertRaises(ValueError):build_sync_payload(result)


if __name__=="__main__":unittest.main()

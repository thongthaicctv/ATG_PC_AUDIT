import tempfile,unittest
from pathlib import Path
from core.sync_queue import SyncQueue


class SyncQueueTests(unittest.TestCase):
    def test_encrypted_deduplicated_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            q=SyncQueue(Path(tmp));payload={"audit_id":"audit-1","profile":{"employee_code":"NV01"}};q.put(payload,"NETWORK_ERROR","offline");q.put(payload,"DEVICE_PENDING","pending");self.assertEqual(q.count(),1);self.assertNotIn("NV01",next(Path(tmp).glob("*.queue")).read_text(encoding="utf-8"));self.assertEqual(q.items()[0][1],payload);q.remove("audit-1");self.assertEqual(q.count(),0)


if __name__=="__main__":unittest.main()

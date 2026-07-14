import tempfile,unittest
from pathlib import Path
from core.license_cache import LicenseCache
from core.license_models import LicenseResult,LicenseStatus


class LicenseCacheTests(unittest.TestCase):
    def test_dpapi_round_trip_and_wrong_device(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"cache.dat";cache=LicenseCache(path);result=LicenseResult(LicenseStatus.VALID_PERMANENT,True,"ATG-PC-AAAA-BBBB-CCCC-DDDD-EEEE",source="ONLINE");cache.save(result)
            self.assertNotIn(b"ATG-PC-AAAA",path.read_bytes());self.assertTrue(cache.load(result.device_id).is_valid);self.assertFalse(cache.load("ATG-PC-1111-2222-3333-4444-5555").is_valid)

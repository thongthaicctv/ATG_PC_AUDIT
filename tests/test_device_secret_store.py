import tempfile,unittest
from pathlib import Path
from core.device_secret_store import DeviceSecretStore


class DeviceSecretStoreTests(unittest.TestCase):
    def test_dpapi_secret_is_stable_and_not_plaintext(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"secret.dat";store=DeviceSecretStore(path);one=store.get_or_create();two=store.get_or_create();self.assertEqual(one,two);self.assertEqual(len(one),64);self.assertNotIn(one.encode(),path.read_bytes())


if __name__=="__main__":unittest.main()

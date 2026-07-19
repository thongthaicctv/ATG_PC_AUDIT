import unittest
from core.zalo_launcher import normalize_vietnam_phone


class PhoneTests(unittest.TestCase):
    def test_supported_formats(self):
        for value in ("0912345678","+84912345678","84912345678","0912 345 678","0912.345.678","0912-345-678"):
            self.assertEqual(normalize_vietnam_phone(value),"0912345678")
    def test_invalid(self):
        for value in ("","abc","123","+84123"):
            with self.assertRaises(ValueError):normalize_vietnam_phone(value)

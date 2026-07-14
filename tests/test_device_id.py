import re
import unittest
from core.device_id import build_device_identity,normalize_hardware_value


class DeviceIdTests(unittest.TestCase):
    def test_stable_and_does_not_use_mac_or_name(self):
        base={"uuid":"u-1","bios":"b-1","board":"m-1","cpu":"c-1","computer_name":"PC1","mac":"AA"}
        other=dict(base,computer_name="PC2",mac="BB")
        self.assertEqual(build_device_identity(base).device_id,build_device_identity(other).device_id)
        self.assertRegex(build_device_identity(base).device_id,r"^ATG-PC-(?:[0-9A-F]{4}-){4}[0-9A-F]{4}$")
    def test_invalid_and_fallback(self):
        self.assertEqual(normalize_hardware_value("To be filled by O.E.M."),"")
        result=build_device_identity({"machine_guid":"guid-1"});self.assertTrue(result.is_fallback);self.assertEqual(result.confidence,"LOW")

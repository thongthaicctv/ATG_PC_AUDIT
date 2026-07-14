import unittest

from core.office_license_checker import normalize_office_status, parse_ospp


class OfficeLicenseTests(unittest.TestCase):
    def test_status_normalization(self):
        self.assertEqual(normalize_office_status("---LICENSED---"), "Đã kích hoạt")
        self.assertEqual(normalize_office_status("---UNLICENSED---"), "Chưa kích hoạt")
        self.assertEqual(normalize_office_status("OOB_GRACE"), "Đang trong thời gian Grace")
        self.assertEqual(normalize_office_status("EXPIRED"), "Hết hạn")

    def test_parse_multiple_ospp_products_and_mask_keys(self):
        output = """LICENSE NAME: Office 21, Office21ProPlus2021VL_KMS_Client edition
LICENSE DESCRIPTION: Office 21, VOLUME_KMSCLIENT channel
LICENSE STATUS: ---LICENSED---
Last 5 characters of installed product key: ABCDE
------------------------------------------------------------
LICENSE NAME: Office 21, VisioPro2021VL edition
LICENSE STATUS: ---OOB_GRACE---
Last 5 characters of installed product key: 12345
"""
        rows = parse_ospp(output)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["partial_key"], "XXXXX-XXXXX-XXXXX-XXXXX-ABCDE")
        self.assertEqual(rows[1]["activation_status"], "Đang trong thời gian Grace")


if __name__ == "__main__": unittest.main()

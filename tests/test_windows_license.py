import unittest

from core.windows_license_checker import classify_channel, mask_key


class WindowsLicenseTests(unittest.TestCase):
    def test_full_key_is_never_returned(self):
        self.assertEqual(mask_key("AAAAA-BBBBB-CCCCC-DDDDD-3V66T"), "XXXXX-XXXXX-XXXXX-XXXXX-3V66T")

    def test_channels(self):
        self.assertEqual(classify_channel("RETAIL channel"), "Retail")
        self.assertEqual(classify_channel("OEM_DM channel"), "OEM_DM")
        self.assertEqual(classify_channel("VOLUME_KMSCLIENT channel"), "Volume KMS Client")
        self.assertEqual(classify_channel("VOLUME_MAK channel"), "Volume MAK")
        self.assertEqual(classify_channel("TIMEBASED_EVAL channel"), "Evaluation")


if __name__ == "__main__": unittest.main()

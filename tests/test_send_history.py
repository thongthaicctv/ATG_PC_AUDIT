import unittest
from core.send_history import mask_email,mask_phone


class SendHistoryTests(unittest.TestCase):
    def test_masks(self):self.assertEqual(mask_phone("0912345678"),"0912***678");self.assertEqual(mask_email("quantri@congty.vn"),"q***i@congty.vn")

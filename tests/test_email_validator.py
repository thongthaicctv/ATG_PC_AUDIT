import unittest
from core.gmail_launcher import valid_email


class EmailTests(unittest.TestCase):
    def test_valid_and_blank(self):self.assertTrue(valid_email("quantri@congty.vn"));self.assertTrue(valid_email(""))
    def test_invalid(self):self.assertFalse(valid_email("quan tri@congty.vn"));self.assertFalse(valid_email("abc@"))

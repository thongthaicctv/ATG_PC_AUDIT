import unittest
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from core.clipboard_manager import copy_text


class ClipboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_copy_text(self):self.assertTrue(copy_text("ATG test"));self.assertEqual(QApplication.clipboard().text(),"ATG test")

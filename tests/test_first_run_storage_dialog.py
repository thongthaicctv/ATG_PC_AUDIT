import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication
from ui.first_run_storage_dialog import FirstRunStorageDialog


class FirstRunStorageDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_new_database_path_follows_custom_data_folder(self):
        with patch("ui.first_run_storage_dialog.detect_legacy_storage",return_value=[]):
            dialog=FirstRunStorageDialog()
            dialog.new.setChecked(True)
            dialog.data_root.setText(r"D:\ATG_CUSTOM")
            self.assertEqual(Path(dialog.database_file.text()),Path(r"D:\ATG_CUSTOM\database\atg_pc_audit_master.db"))
            self.assertEqual(dialog.database_label.text(),"Lưu database tại:")
            dialog.close()

    def test_existing_mode_keeps_selected_database_file(self):
        legacy=Path(r"D:\OLD\company.db")
        with patch("ui.first_run_storage_dialog.detect_legacy_storage",return_value=[legacy]):
            dialog=FirstRunStorageDialog()
            dialog.existing.setChecked(True)
            dialog.data_root.setText(r"D:\NEW_ROOT")
            self.assertEqual(Path(dialog.database_file.text()),legacy)
            self.assertEqual(dialog.database_label.text(),"Database có sẵn:")
            dialog.close()


if __name__ == "__main__":unittest.main()

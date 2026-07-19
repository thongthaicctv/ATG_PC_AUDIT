import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class StartupAccessTests(unittest.TestCase):
    def test_employee_without_license_skips_storage_setup(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(main, "has_activated_admin_license", return_value=False):
            self.assertFalse(main.should_show_storage_setup(Path(tmp)/"missing.json"))

    def test_activated_admin_without_bootstrap_sees_storage_setup(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(main, "has_activated_admin_license", return_value=True):
            self.assertTrue(main.should_show_storage_setup(Path(tmp)/"missing.json"))

    def test_existing_bootstrap_never_reopens_setup(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(main, "has_activated_admin_license", return_value=True):
            bootstrap=Path(tmp)/"bootstrap.json";bootstrap.write_text("{}",encoding="utf-8")
            self.assertFalse(main.should_show_storage_setup(bootstrap))


if __name__ == "__main__":
    unittest.main()

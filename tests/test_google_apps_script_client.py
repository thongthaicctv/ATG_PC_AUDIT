import unittest
from core.google_apps_script_client import GoogleAppsScriptClient


class ClientTests(unittest.TestCase):
    def test_url_must_be_https_exec(self):
        with self.assertRaises(ValueError):GoogleAppsScriptClient("http://example.com/exec")
        with self.assertRaises(ValueError):GoogleAppsScriptClient("https://example.com/dev")
    def test_blank_url_is_safe(self):self.assertEqual(GoogleAppsScriptClient("").health_check().code,"NOT_CONFIGURED")


if __name__=="__main__":unittest.main()

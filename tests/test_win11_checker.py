import unittest
from unittest.mock import patch

from core.win11_checker import evaluate_windows11
from models.audit_result import AuditResult


def result_template():
    return AuditResult(
        cpu={"name": "Supported CPU", "architecture": "64-bit", "cores": 4, "max_clock_mhz": 2400},
        ram_summary={"total_gb": 16},
        windows={"system_drive_total_gb": 256, "system_drive_free_gb": 100},
        disks=[{"is_system": True, "partition_style": "GPT", "disk_type": "SSD"}],
        security={"firmware_mode": "UEFI", "secure_boot_capable": True, "secure_boot_enabled": True,
                  "tpm_present": True, "tpm_enabled": True, "tpm_ready": True, "tpm_spec_version": "2.0"},
    )


class Windows11CheckerTests(unittest.TestCase):
    @patch("core.win11_checker._cpu_supported", return_value=("Đạt", "mock"))
    def test_all_requirements_pass(self, _):
        readiness, recommendations = evaluate_windows11(result_template())
        self.assertEqual(readiness["overall"], "ĐỦ ĐIỀU KIỆN CÀI WINDOWS 11")
        self.assertFalse(recommendations)

    @patch("core.win11_checker._cpu_supported", return_value=("Đạt", "mock"))
    def test_tpm_12_fails(self, _):
        result = result_template(); result.security["tpm_spec_version"] = "1.2"
        readiness, recommendations = evaluate_windows11(result)
        self.assertEqual(readiness["overall"], "KHÔNG ĐỦ ĐIỀU KIỆN CÀI WINDOWS 11")
        self.assertTrue(any("không khuyến nghị bypass" in x for x in recommendations))

    @patch("core.win11_checker._cpu_supported", return_value=("Đạt", "mock"))
    def test_legacy_bios_and_secure_boot_off_fail(self, _):
        result = result_template(); result.security.update(firmware_mode="Legacy/Không xác định", secure_boot_enabled=False)
        readiness, _ = evaluate_windows11(result)
        failed = {x["condition"] for x in readiness["conditions"] if x["status"] == "Không đạt"}
        self.assertIn("Firmware UEFI", failed)
        secure_boot = next(x for x in readiness["conditions"] if x["condition"] == "Secure Boot Enabled")
        self.assertEqual(secure_boot["status"], "Khuyến nghị bật")

    @patch("core.win11_checker._cpu_supported", return_value=("Chưa xác định", "CPU chưa có"))
    def test_unknown_cpu_never_passes(self, _):
        readiness, recommendations = evaluate_windows11(result_template())
        self.assertEqual(readiness["overall"], "CẦN KIỂM TRA THÊM")
        self.assertTrue(any("CPU" in x for x in recommendations))

    @patch("core.win11_checker._cpu_supported", return_value=("Đạt", "mock"))
    def test_upgrade_recommendations(self, _):
        result = result_template(); result.ram_summary["total_gb"] = 4
        result.windows["system_drive_free_gb"] = 10; result.disks[0]["disk_type"] = "HDD"
        _, recommendations = evaluate_windows11(result)
        self.assertEqual(len(recommendations), 3)

    @patch("core.win11_checker._cpu_supported", return_value=("Đạt", "mock"))
    def test_secure_boot_disabled_is_recommendation_not_hard_fail(self, _):
        result = result_template(); result.security["secure_boot_enabled"] = False
        readiness, recommendations = evaluate_windows11(result)
        self.assertEqual(readiness["overall"], "ĐỦ ĐIỀU KIỆN CÀI WINDOWS 11")
        self.assertTrue(any("Secure Boot" in x for x in recommendations))

    @patch("core.win11_checker._cpu_supported", return_value=("Đạt", "mock"))
    def test_running_windows11_with_unreadable_tpm_is_not_reported_hard_fail(self, _):
        result = result_template(); result.windows["is_windows11"] = True
        result.security.update(tpm_present=None, tpm_enabled=None, tpm_ready=None, tpm_spec_version="Không xác định")
        readiness, _ = evaluate_windows11(result)
        self.assertEqual(readiness["overall"], "CẦN KIỂM TRA THÊM")
        self.assertTrue(readiness["display_overall"].startswith("MÁY ĐANG CHẠY WINDOWS 11"))


if __name__ == "__main__":
    unittest.main()

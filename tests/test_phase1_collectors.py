import unittest
from unittest.mock import patch

from core.hardware_collector import collect_computer, collect_cpu, collect_ram
from core.resource_utils import resource_path


class Phase1CollectorTests(unittest.TestCase):
    @patch("core.hardware_collector._wmi_rows")
    def test_computer_maps_wmi(self, rows):
        rows.side_effect = [
            [{"Manufacturer": "ATG", "Model": "M1", "SystemSKUNumber": "SKU", "SystemType": "x64", "UserName": "ATG\\user", "Domain": "ATG"}],
            [{"IdentifyingNumber": "SERIAL1", "UUID": "UUID1"}],
        ]
        result = collect_computer()
        self.assertEqual(result["serial_number"], "SERIAL1")
        self.assertEqual(result["manufacturer"], "ATG")

    @patch("core.hardware_collector._wmi_rows")
    def test_cpu_totals_multiple_sockets(self, rows):
        rows.return_value = [
            {"Name": "CPU", "Manufacturer": "Vendor", "NumberOfCores": 4, "NumberOfLogicalProcessors": 8, "MaxClockSpeed": 3000, "AddressWidth": 64},
            {"Name": "CPU", "Manufacturer": "Vendor", "NumberOfCores": 4, "NumberOfLogicalProcessors": 8, "MaxClockSpeed": 3000, "AddressWidth": 64},
        ]
        result = collect_cpu()
        self.assertEqual((result["sockets"], result["cores"], result["threads"]), (2, 8, 16))

    @patch("core.hardware_collector.psutil.virtual_memory")
    @patch("core.hardware_collector._wmi_rows")
    def test_ram_is_converted_to_gb(self, rows, memory):
        rows.return_value = [{"DeviceLocator": "DIMM 0", "Capacity": 8 * 1024**3}]
        memory.return_value.total = 8 * 1024**3
        summary, modules = collect_ram()
        self.assertEqual(summary["total_gb"], 8)
        self.assertEqual(modules[0]["capacity_gb"], 8)

    def test_resource_path_is_absolute(self):
        self.assertTrue(resource_path("config/app_config.json").is_absolute())


if __name__ == "__main__":
    unittest.main()


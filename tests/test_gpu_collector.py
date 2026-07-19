import unittest
from unittest.mock import patch

from core.hardware_collector import collect_gpu


class GpuCollectorTests(unittest.TestCase):
    def test_collects_active_gpu_and_vram(self):
        row={"Name":"Intel Iris Xe","VideoProcessor":"Intel GPU","AdapterRAM":2*1024**3,
             "DriverVersion":"31.0.1","DriverDate":"20260718000000.000000+000",
             "VideoModeDescription":"1920 x 1080 x 4294967296 colors",
             "CurrentHorizontalResolution":1920,"CurrentVerticalResolution":1080,
             "Status":"OK","Availability":3,"PNPDeviceID":"PCI\\VEN_8086"}
        with patch("core.hardware_collector._wmi_rows",return_value=[row]):gpus=collect_gpu()
        self.assertEqual(gpus[0]["name"],"Intel Iris Xe")
        self.assertEqual(gpus[0]["adapter_ram_gb"],2.0)
        self.assertEqual(gpus[0]["resolution"],"1920 x 1080")
        self.assertTrue(gpus[0]["is_active"])


if __name__ == "__main__":unittest.main()

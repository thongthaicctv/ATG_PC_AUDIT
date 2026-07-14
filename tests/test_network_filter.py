import unittest

from core.network_collector import classify_adapter, choose_primary_adapter, normalize_mac, validate_ip_plan


class NetworkFilterTests(unittest.TestCase):
    def test_mac_is_normalized_and_zero_mac_rejected(self):
        self.assertEqual(normalize_mac("aa:bb:cc:dd:ee:ff"), "AA-BB-CC-DD-EE-FF")
        self.assertEqual(normalize_mac("00-00-00-00-00-00"), "")

    def test_physical_ethernet_and_wifi_are_classified(self):
        self.assertEqual(classify_adapter({"name": "Ethernet", "description": "Intel Ethernet", "physical_adapter": True}), "Ethernet vật lý")
        self.assertEqual(classify_adapter({"name": "Wi-Fi", "description": "Intel Wireless", "physical_adapter": True}), "Wi-Fi vật lý")

    def test_virtual_adapters_are_not_physical(self):
        self.assertEqual(classify_adapter({"description": "VMware Virtual Ethernet Adapter", "physical_adapter": False}), "VMware")
        self.assertEqual(classify_adapter({"description": "TAP-Windows VPN", "physical_adapter": False}), "VPN")

    def test_primary_prefers_connected_ethernet(self):
        adapters = [
            {"interface_index": 8, "interface_type": "Wi-Fi vật lý", "connected": True, "ipv4": ["192.168.1.20"], "default_gateway": ["192.168.1.1"], "mac_address": "AA-BB-CC-DD-EE-01"},
            {"interface_index": 12, "interface_type": "Ethernet vật lý", "connected": True, "ipv4": ["192.168.1.10"], "default_gateway": ["192.168.1.1"], "mac_address": "AA-BB-CC-DD-EE-02"},
        ]
        self.assertEqual(choose_primary_adapter(adapters), 12)

    def test_apipa_and_virtual_are_never_primary(self):
        adapters = [
            {"interface_index": 1, "interface_type": "Ethernet vật lý", "connected": True, "ipv4": ["169.254.1.2"], "default_gateway": [], "mac_address": "AA-BB-CC-DD-EE-01"},
            {"interface_index": 2, "interface_type": "VMware", "connected": True, "ipv4": ["10.0.0.2"], "default_gateway": ["10.0.0.1"], "mac_address": "AA-BB-CC-DD-EE-02"},
        ]
        self.assertIsNone(choose_primary_adapter(adapters))

    def test_ip_plan_requires_same_subnet(self):
        self.assertTrue(validate_ip_plan("10.10.1.20", "24", "10.10.1.1")[0])
        self.assertFalse(validate_ip_plan("10.10.1.20", "24", "10.10.2.1")[0])


if __name__ == "__main__":
    unittest.main()

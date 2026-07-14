import ipaddress
import json
import logging
import re
import subprocess
from typing import Any, Dict, List, Optional

LOG = logging.getLogger(__name__)

VIRTUAL_MARKERS = ("vmware", "virtualbox", "hyper-v", "vethernet", "vpn", "tap-", "wireguard", "wsl", "loopback", "tunnel", "pseudo", "teredo", "bluetooth")
WIFI_MARKERS = ("wi-fi", "wifi", "wireless", "wlan", "802.11")


def normalize_mac(value: Any) -> str:
    chars = re.sub(r"[^0-9A-Fa-f]", "", str(value or "")).upper()
    if len(chars) != 12 or chars == "0" * 12:
        return ""
    return "-".join(chars[i:i + 2] for i in range(0, 12, 2))


def classify_adapter(adapter: Dict[str, Any]) -> str:
    text = " ".join(str(adapter.get(k) or "") for k in ("name", "description", "pnp_device_id")).lower()
    if "bluetooth" in text:
        return "Bluetooth"
    if "vmware" in text:
        return "VMware"
    if "virtualbox" in text:
        return "VirtualBox"
    if "hyper-v" in text or "vethernet" in text:
        return "Hyper-V"
    if "wsl" in text:
        return "WSL"
    if "vpn" in text or "tap-" in text or "wireguard" in text:
        return "VPN"
    if "loopback" in text:
        return "Loopback"
    if "tunnel" in text or "teredo" in text or "pseudo" in text:
        return "Tunnel"
    if any(x in text for x in WIFI_MARKERS):
        return "Wi-Fi vật lý" if adapter.get("physical_adapter") else "Wi-Fi ảo"
    return "Ethernet vật lý" if adapter.get("physical_adapter") else "Card mạng khác"


def _is_valid_ipv4(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
        return ip.version == 4 and not ip.is_loopback and not ip.is_link_local
    except ValueError:
        return False


def choose_primary_adapter(adapters: List[Dict[str, Any]]) -> Optional[int]:
    candidates = []
    for adapter in adapters:
        kind = adapter.get("interface_type")
        ipv4 = next((x for x in adapter.get("ipv4", []) if _is_valid_ipv4(x)), None)
        if kind not in ("Ethernet vật lý", "Wi-Fi vật lý") or not adapter.get("connected") or not ipv4:
            continue
        if not normalize_mac(adapter.get("mac_address")) or not adapter.get("default_gateway"):
            continue
        candidates.append((0 if kind == "Ethernet vật lý" else 1, int(adapter.get("interface_index") or 999999)))
    return min(candidates)[1] if candidates else None


def _run_network_query():
    script = r"""
$rows = Get-CimInstance Win32_NetworkAdapter | ForEach-Object {
  $a=$_; $c=Get-CimInstance Win32_NetworkAdapterConfiguration -Filter "Index=$($a.Index)" -ErrorAction SilentlyContinue
  [pscustomobject]@{Name=$a.NetConnectionID;Description=$a.Description;PhysicalAdapter=$a.PhysicalAdapter;
    NetConnectionStatus=$a.NetConnectionStatus;Speed=$a.Speed;MACAddress=$a.MACAddress;InterfaceIndex=$a.InterfaceIndex;
    PNPDeviceID=$a.PNPDeviceID;Manufacturer=$a.Manufacturer;DriverVersion=$a.DriverVersion;
    IPAddress=@($c.IPAddress);IPSubnet=@($c.IPSubnet);DefaultIPGateway=@($c.DefaultIPGateway);
    DNSServerSearchOrder=@($c.DNSServerSearchOrder);DHCPEnabled=$c.DHCPEnabled;DHCPServer=$c.DHCPServer}
}; @($rows) | ConvertTo-Json -Depth 4 -Compress
"""
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "Không truy vấn được card mạng")
    return json.loads(completed.stdout.strip() or "[]")


def collect_network() -> tuple[List[Dict[str, Any]], Optional[int]]:
    try:
        rows = _run_network_query()
        if isinstance(rows, dict):
            rows = [rows]
    except Exception:
        LOG.exception("Không thu thập được card mạng")
        return [], None
    adapters = []
    for row in rows:
        addresses = row.get("IPAddress") or []
        if isinstance(addresses, str):
            addresses = [addresses]
        addresses = [str(x) for x in addresses if x]
        subnets = row.get("IPSubnet") or []
        if isinstance(subnets, str):
            subnets = [subnets]
        subnets = [str(x) for x in subnets if x]
        gateways = row.get("DefaultIPGateway") or []
        dns = row.get("DNSServerSearchOrder") or []
        if isinstance(gateways, str): gateways = [gateways]
        if isinstance(dns, str): dns = [dns]
        gateways = [str(x) for x in gateways if x]
        dns = [str(x) for x in dns if x]
        adapter = {
            "name": row.get("Name") or "Không xác định", "description": row.get("Description") or "Không xác định",
            "physical_adapter": bool(row.get("PhysicalAdapter")), "connected": row.get("NetConnectionStatus") == 2,
            "connection_status": "Connected" if row.get("NetConnectionStatus") == 2 else "Disconnected",
            "link_speed_mbps": round(int(row.get("Speed") or 0) / 1_000_000, 1),
            "mac_address": normalize_mac(row.get("MACAddress")) or "Không có",
            "ipv4": [x for x in addresses if ":" not in x], "ipv6": [x for x in addresses if ":" in x],
            "prefix_or_mask": subnets, "default_gateway": gateways, "dns_servers": dns,
            "dhcp_enabled": row.get("DHCPEnabled"), "dhcp_server": row.get("DHCPServer") or "Không có",
            "interface_index": row.get("InterfaceIndex") or row.get("Index"),
            "driver_version": row.get("DriverVersion") or "Không xác định",
            "manufacturer": row.get("Manufacturer") or "Không xác định", "pnp_device_id": row.get("PNPDeviceID") or "",
        }
        adapter["interface_type"] = classify_adapter(adapter)
        adapters.append(adapter)
    adapters.sort(key=lambda x: (x["interface_type"] not in ("Ethernet vật lý", "Wi-Fi vật lý"), not x["connected"], x["name"]))
    return adapters, choose_primary_adapter(adapters)


def validate_ip_plan(ip_value: str, prefix: str, gateway: str) -> tuple[bool, str]:
    try:
        interface = ipaddress.ip_interface(f"{ip_value}/{int(prefix)}")
        gateway_ip = ipaddress.ip_address(gateway)
    except (ValueError, TypeError):
        return False, "IP, Prefix hoặc Gateway không đúng định dạng."
    if interface.version != 4 or gateway_ip.version != 4:
        return False, "Quy hoạch hiện chỉ chấp nhận IPv4."
    if gateway_ip not in interface.network:
        return False, "IP dự kiến và Gateway không cùng subnet."
    if interface.ip == gateway_ip:
        return False, "IP dự kiến không được trùng Gateway."
    return True, "Thông tin IP dự kiến hợp lệ."

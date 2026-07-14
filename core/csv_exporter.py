import csv
import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

LOG = logging.getLogger(__name__)
SCHEMA_VERSION = "1.0"
APP_VERSION = "1.0.0"
FORMULA_FIELDS = {"asset_code", "assigned_user", "department", "location", "auditor", "note", "switch_name", "switch_port", "network_note"}


def escape_excel_formula(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")): return "'" + value
    return value


def unescape_excel_formula(value):
    if isinstance(value, str) and len(value) > 1 and value[0] == "'" and value[1] in "=+-@": return value[1:]
    return value


def canonical_hash(data: Dict[str, Any]) -> str:
    clean = {k: ("" if v is None else str(v)) for k, v in data.items() if k != "record_sha256"}
    canonical = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


CSV_FIELDS = [
    "schema_version","app_version","export_id","audit_id","exported_at_iso","audit_time_iso","audit_date_display","source_computer_name",
    "asset_code","assigned_user","department","location","auditor","note",
    "computer_name","manufacturer","model","system_sku","serial_number","uuid","system_type","mainboard_manufacturer","mainboard_product","mainboard_serial","bios_version","bios_release_date",
    "os_name","os_edition","os_display_version","os_version","os_build","os_architecture","os_install_date","system_drive",
    "cpu_name","cpu_manufacturer","cpu_cores","cpu_threads","cpu_max_clock_mhz","ram_total_gb","ram_slots_used",
    "system_disk_model","system_disk_media_type","system_disk_bus_type","system_disk_partition_style","system_disk_size_gb","system_disk_free_gb","system_disk_used_percent",
    "firmware_mode","secure_boot_status","tpm_present","tpm_enabled","tpm_ready","tpm_version","win11_status","win11_block_reasons","recommendations",
    "windows_activation_status","windows_license_name","windows_license_type","windows_license_channel","windows_partial_key","windows_permanent_activation","windows_expiration","windows_grace_remaining",
    "office_installed","office_product_summary","office_activation_summary","office_license_type_summary","office_partial_keys","office_expiration_summary",
    "primary_adapter_name","primary_adapter_type","primary_mac","current_ipv4","prefix_length","subnet_mask","default_gateway","dns_servers","dhcp_enabled","dhcp_server","link_speed",
    "planned_vlan","planned_ipv4","planned_prefix","planned_gateway","planned_dns_1","planned_dns_2","switch_name","switch_port","network_socket","deployment_status","network_note",
    "ram_details_json","disks_details_json","gpu_details_json","network_adapters_json","windows_license_details_json","office_license_details_json","win11_checks_json","record_sha256",
]


def _join(value):
    if isinstance(value, list): return ", ".join(str(x) for x in value)
    return "" if value is None else str(value)


def build_csv_record(result) -> Dict[str, Any]:
    d = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    m,c,cpu,ram,w,bios,sec = d.get("metadata",{}),d.get("computer",{}),d.get("cpu",{}),d.get("ram_summary",{}),d.get("windows",{}),d.get("bios",{}),d.get("security",{})
    disks=d.get("disks",[]); system_disk=next((x for x in disks if x.get("is_system")), disks[0] if disks else {})
    nets=d.get("network_adapters",[]); primary=next((x for x in nets if x.get("interface_index")==d.get("primary_adapter_index")),{})
    wl=d.get("windows_license",{}); offices=d.get("office_licenses",[]); plan=d.get("ip_plan",{}); checks=d.get("windows11",{}).get("conditions",[])
    office_safe=[]
    for item in offices:
        office_safe.append({k:v for k,v in item.items() if k not in ("user_email","tenant_id")})
    failed=[x.get("condition") for x in checks if x.get("status") in ("Không đạt","Chưa xác định") and x.get("required_for_overall",True)]
    size=float(system_disk.get("capacity_gb") or w.get("system_drive_total_gb") or 0); free=float(w.get("system_drive_free_gb") or 0)
    prefix_values=primary.get("prefix_or_mask") or []
    record={
        "schema_version":SCHEMA_VERSION,"app_version":APP_VERSION,"export_id":str(uuid.uuid4()),"audit_id":d.get("audit_id") or str(uuid.uuid4()),
        "exported_at_iso":datetime.now().isoformat(timespec="seconds"),"audit_time_iso":d.get("audited_at"),"audit_date_display":m.get("audit_date_display") or m.get("audit_date"),"source_computer_name":c.get("computer_name"),
        "asset_code":m.get("asset_code"),"assigned_user":m.get("user"),"department":m.get("department"),"location":m.get("location"),"auditor":m.get("auditor"),"note":m.get("notes"),
        "computer_name":c.get("computer_name") or "UNKNOWN-PC","manufacturer":c.get("manufacturer"),"model":c.get("model"),"system_sku":c.get("system_sku"),"serial_number":c.get("serial_number"),"uuid":c.get("uuid"),"system_type":c.get("system_type"),
        "mainboard_manufacturer":bios.get("mainboard_manufacturer"),"mainboard_product":bios.get("mainboard_product"),"mainboard_serial":bios.get("mainboard_serial"),"bios_version":bios.get("bios_version"),"bios_release_date":bios.get("bios_release_date"),
        "os_name":w.get("edition"),"os_edition":w.get("edition"),"os_display_version":w.get("display_version"),"os_version":w.get("version"),"os_build":w.get("build_number"),"os_architecture":w.get("architecture"),"os_install_date":w.get("installation_date"),"system_drive":w.get("system_drive"),
        "cpu_name":cpu.get("name"),"cpu_manufacturer":cpu.get("manufacturer"),"cpu_cores":cpu.get("cores"),"cpu_threads":cpu.get("threads"),"cpu_max_clock_mhz":cpu.get("max_clock_mhz"),"ram_total_gb":ram.get("total_gb"),"ram_slots_used":ram.get("module_count"),
        "system_disk_model":system_disk.get("model"),"system_disk_media_type":system_disk.get("disk_type") or system_disk.get("media_type"),"system_disk_bus_type":system_disk.get("bus_type"),"system_disk_partition_style":system_disk.get("partition_style"),"system_disk_size_gb":size,"system_disk_free_gb":free,"system_disk_used_percent":round((size-free)/size*100,2) if size else "",
        "firmware_mode":sec.get("firmware_mode"),"secure_boot_status":sec.get("secure_boot_enabled"),"tpm_present":sec.get("tpm_present"),"tpm_enabled":sec.get("tpm_enabled"),"tpm_ready":sec.get("tpm_ready"),"tpm_version":sec.get("tpm_spec_version"),"win11_status":d.get("windows11",{}).get("overall"),"win11_block_reasons":_join(failed),"recommendations":_join(d.get("recommendations",[])),
        "windows_activation_status":wl.get("activation_status"),"windows_license_name":wl.get("edition"),"windows_license_type":wl.get("license_type"),"windows_license_channel":wl.get("license_channel"),"windows_partial_key":wl.get("partial_key"),"windows_permanent_activation":wl.get("permanent_activation"),"windows_expiration":wl.get("expiration"),"windows_grace_remaining":wl.get("grace_remaining_minutes"),
        "office_installed":bool(d.get("office_products")),"office_product_summary":_join(dict.fromkeys(x.get("product_name","") for x in offices)),"office_activation_summary":_join(dict.fromkeys(x.get("activation_status","") for x in offices)),"office_license_type_summary":_join(dict.fromkeys(x.get("mechanism","") for x in offices)),"office_partial_keys":_join(x.get("partial_key","") for x in offices),"office_expiration_summary":_join(x.get("expiration","") for x in offices),
        "primary_adapter_name":primary.get("name"),"primary_adapter_type":primary.get("interface_type"),"primary_mac":primary.get("mac_address"),"current_ipv4":_join(primary.get("ipv4",[])),"prefix_length":_join(prefix_values),"subnet_mask":_join(prefix_values),"default_gateway":_join(primary.get("default_gateway",[])),"dns_servers":_join(primary.get("dns_servers",[])),"dhcp_enabled":primary.get("dhcp_enabled"),"dhcp_server":primary.get("dhcp_server"),"link_speed":primary.get("link_speed_mbps"),
        "planned_vlan":plan.get("vlan"),"planned_ipv4":plan.get("planned_ip"),"planned_prefix":plan.get("prefix"),"planned_gateway":plan.get("gateway"),"planned_dns_1":plan.get("dns1"),"planned_dns_2":plan.get("dns2"),"switch_name":plan.get("switch_name"),"switch_port":plan.get("switch_port"),"network_socket":plan.get("network_socket"),"deployment_status":plan.get("deployment_status"),"network_note":plan.get("notes"),
        "ram_details_json":json.dumps(d.get("ram_modules",[]),ensure_ascii=False),"disks_details_json":json.dumps(disks,ensure_ascii=False),"gpu_details_json":json.dumps(d.get("gpu",[]),ensure_ascii=False),"network_adapters_json":json.dumps(nets,ensure_ascii=False),"windows_license_details_json":json.dumps(wl,ensure_ascii=False),"office_license_details_json":json.dumps(office_safe,ensure_ascii=False),"win11_checks_json":json.dumps(checks,ensure_ascii=False),
    }
    for key in FORMULA_FIELDS: record[key]=escape_excel_formula(record.get(key,""))
    record={key:("" if record.get(key) is None else record.get(key)) for key in CSV_FIELDS if key!="record_sha256"}
    record["record_sha256"]=canonical_hash(record)
    return record


def default_export_directory() -> Path:
    executable_dir=Path(sys.executable if getattr(sys,"frozen",False) else Path(__file__).resolve().parents[1]).parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parents[1]
    candidate=executable_dir/"KetQuaThuThap"
    try: candidate.mkdir(parents=True,exist_ok=True); test=candidate/".write_test"; test.write_text("ok"); test.unlink(); return candidate
    except OSError:
        fallback=Path.home()/"Documents"/"ATG_PC_AUDIT"/"KetQuaThuThap"; fallback.mkdir(parents=True,exist_ok=True); return fallback


def export_csv(result, folder: Path) -> Path:
    record=build_csv_record(result); asset=str(record.get("asset_code","")).strip()
    if not asset: raise ValueError("Mã tài sản không được để trống khi xuất CSV.")
    folder.mkdir(parents=True,exist_ok=True); stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    clean=lambda s: "".join("_" if ch in '\\/:*?\"<>|' else ch for ch in str(s)).strip(" ._")
    base=f"PC_AUDIT_{clean(asset)}_{clean(record.get('computer_name') or 'UNKNOWN-PC')}_{stamp}"; path=folder/f"{base}.csv"; n=1
    while path.exists(): path=folder/f"{base}_{n:02d}.csv"; n+=1
    LOG.info("CSV export started")
    try:
        with path.open("w",encoding="utf-8-sig",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=CSV_FIELDS,quoting=csv.QUOTE_ALL); writer.writeheader(); writer.writerow(record)
        LOG.info("CSV export completed: %s",path.name); return path
    except Exception: LOG.exception("CSV export failed"); raise

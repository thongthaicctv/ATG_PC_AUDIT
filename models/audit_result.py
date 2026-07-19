from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List
import uuid


@dataclass
class AuditResult:
    metadata: Dict[str, Any] = field(default_factory=dict)
    computer: Dict[str, Any] = field(default_factory=dict)
    cpu: Dict[str, Any] = field(default_factory=dict)
    ram_summary: Dict[str, Any] = field(default_factory=dict)
    ram_modules: List[Dict[str, Any]] = field(default_factory=list)
    bios: Dict[str, Any] = field(default_factory=dict)
    disks: List[Dict[str, Any]] = field(default_factory=list)
    gpu: List[Dict[str, Any]] = field(default_factory=list)
    security: Dict[str, Any] = field(default_factory=dict)
    windows: Dict[str, Any] = field(default_factory=dict)
    windows11: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    network_adapters: List[Dict[str, Any]] = field(default_factory=list)
    primary_adapter_index: Any = None
    ip_plan: Dict[str, Any] = field(default_factory=dict)
    windows_license: Dict[str, Any] = field(default_factory=dict)
    office_products: List[Dict[str, Any]] = field(default_factory=list)
    office_licenses: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    audited_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

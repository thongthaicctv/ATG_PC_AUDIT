from dataclasses import dataclass,field
from typing import Any,Dict


@dataclass
class ApiResult:
    success: bool
    code: str
    message: str = ""
    data: Dict[str,Any] = field(default_factory=dict)
    retryable: bool = False
    server_time: str = ""
    raw_status_code: int = 0


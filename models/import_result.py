from dataclasses import dataclass,field
from typing import Any,Dict

@dataclass
class ImportPreview:
    file_path:str
    record:Dict[str,Any]=field(default_factory=dict)
    status:str="CSV lỗi"
    action:str="skip"
    message:str=""
    hash_verified:bool=False


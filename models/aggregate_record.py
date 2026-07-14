from dataclasses import dataclass,field
from typing import Any,Dict

@dataclass
class AggregateRecord:
    values:Dict[str,Any]=field(default_factory=dict)


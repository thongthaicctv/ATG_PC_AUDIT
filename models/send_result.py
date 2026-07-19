from dataclasses import dataclass


@dataclass
class SendResult:
    method: str
    status: str
    file_path: str
    recipient_masked: str = ""
    message: str = ""

import json
import os
from datetime import datetime
from pathlib import Path


def history_path():
    root=Path(os.environ.get("LOCALAPPDATA") or Path.home())/"ATG_PC_AUDIT"/"send"
    root.mkdir(parents=True,exist_ok=True);return root/"send_history.jsonl"


def mask_phone(value):
    text=str(value or "");return text[:4]+"***"+text[-3:] if len(text)>=8 else "***"


def mask_email(value):
    text=str(value or "")
    if "@" not in text:return ""
    name,domain=text.split("@",1);return (name[:1]+"***"+name[-1:] if len(name)>1 else "***")+"@"+domain


def record_send(audit_id,asset_code,computer_name,method,file_path,recipient,status,error=""):
    masked=mask_phone(recipient) if method=="ZALO" else mask_email(recipient) if method=="GMAIL" else ""
    row={"time":datetime.now().isoformat(timespec="seconds"),"audit_id":audit_id,"asset_code":asset_code,"computer_name":computer_name,"method":method,"file_name":Path(file_path).name,"recipient":masked,"status":status,"error":str(error)[:500]}
    with history_path().open("a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")
    return row

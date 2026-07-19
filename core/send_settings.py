import json,os
from pathlib import Path
from core.resource_utils import resource_path

DEFAULTS={"remember_zalo_phone":False,"zalo_phone":"","remember_admin_email":False,"admin_email":"","default_send_method":"LOCAL","zalo_assisted_mode":True}


def settings_path():
    root=Path(os.environ.get("LOCALAPPDATA") or Path.home())/"ATG_PC_AUDIT"/"config";root.mkdir(parents=True,exist_ok=True);return root/"send_settings.json"


def load_send_settings():
    data=dict(DEFAULTS)
    try:data.update(json.loads(resource_path("config/app_config.json").read_text(encoding="utf-8")).get("send_settings",{}))
    except Exception:pass
    try:data.update(json.loads(settings_path().read_text(encoding="utf-8")))
    except Exception:pass
    return data


def save_send_settings(**updates):
    data=load_send_settings();data.update(updates);settings_path().write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8");return data

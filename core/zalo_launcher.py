import os
import re
import subprocess
import winreg
from pathlib import Path


def normalize_vietnam_phone(value):
    text=re.sub(r"[\s.\-]","",str(value or "").strip())
    if text.startswith("+84"):text="0"+text[3:]
    elif text.startswith("84") and len(text) in (11,12):text="0"+text[2:]
    if not text.isdigit() or len(text) not in (10,11) or not text.startswith("0"):raise ValueError("Số điện thoại không hợp lệ.")
    return text


def _registry_candidates():
    paths=[]
    for root in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
        for key_name in (r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Zalo.exe",r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\Zalo.exe"):
            try:
                with winreg.OpenKey(root,key_name) as key:paths.append(winreg.QueryValue(key,None))
            except OSError:pass
    return paths


def find_zalo_executable():
    candidates=_registry_candidates();local=os.environ.get("LOCALAPPDATA","");program=os.environ.get("PROGRAMFILES","");program86=os.environ.get("PROGRAMFILES(X86)","")
    candidates += [Path(local)/"Programs"/"Zalo"/"Zalo.exe",Path(local)/"Zalo"/"Zalo.exe",Path(program)/"Zalo"/"Zalo.exe",Path(program86)/"Zalo"/"Zalo.exe"]
    start=Path(os.environ.get("APPDATA", ""))/"Microsoft"/"Windows"/"Start Menu"/"Programs"
    if start.exists():candidates += list(start.rglob("Zalo.exe"))
    return next((Path(x) for x in candidates if x and Path(x).is_file()),None)


def launch_zalo(executable=None):
    try:
        from pywinauto import Desktop
        windows=[w for w in Desktop(backend="uia").windows() if "zalo" in str(w.window_text()).lower()]
        if windows:windows[0].set_focus();return None
    except Exception:pass
    path=Path(executable) if executable else find_zalo_executable()
    if not path or not path.is_file():raise FileNotFoundError("Không tìm thấy Zalo Desktop trên máy tính.")
    return subprocess.Popen([str(path)],shell=False)

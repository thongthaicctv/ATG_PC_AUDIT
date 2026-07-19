from pathlib import Path
import time
from PyQt5.QtWidgets import QApplication

_last_text=""


def copy_text(text):
    global _last_text
    _last_text=str(text or "");QApplication.clipboard().setText(_last_text);return True


copy_phone=copy_text
copy_email=copy_text
copy_subject=copy_text
copy_message=copy_text


def copy_file(file_path):
    path=Path(file_path).resolve()
    if not path.is_file():raise FileNotFoundError(path)
    import struct,win32clipboard,win32con
    paths=(str(path)+"\0\0").encode("utf-16le");payload=struct.pack("IiiII",20,0,0,0,1)+paths
    for attempt in range(3):
        try:win32clipboard.OpenClipboard();win32clipboard.EmptyClipboard();win32clipboard.SetClipboardData(win32con.CF_HDROP,payload);win32clipboard.CloseClipboard();return True
        except Exception:
            try:win32clipboard.CloseClipboard()
            except Exception:pass
            if attempt<2:time.sleep(.1)
    return False


def clear_sensitive_clipboard_if_needed():
    global _last_text
    if _last_text and QApplication.clipboard().text()==_last_text:QApplication.clipboard().clear()
    _last_text=""

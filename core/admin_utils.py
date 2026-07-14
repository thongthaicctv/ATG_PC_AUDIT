import ctypes
import logging
import os
import sys

LOG = logging.getLogger(__name__)


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        LOG.exception("Không thể xác định quyền quản trị")
        return False


def restart_as_admin() -> bool:
    if getattr(sys, "frozen", False):
        executable, parameters = sys.executable, ""
    else:
        executable = sys.executable
        parameters = f'"{os.path.abspath(sys.argv[0])}"'
    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, parameters, os.getcwd(), 1
        )
        return result > 32
    except Exception:
        LOG.exception("Không thể khởi động lại với quyền quản trị")
        return False


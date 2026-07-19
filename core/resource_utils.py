import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    if relative_path.replace("\\","/")=="config/app_config.json":
        # Explicit portable deployment wins over a bootstrap left on the PC.
        # This lets administrators copy EXE + data to another machine and have
        # the accompanying catalog/config take effect without extra setup.
        if getattr(sys,"frozen",False):
            exe_dir=Path(sys.executable).resolve().parent
            for candidate in (exe_dir/"data"/"config"/"app_config.json",exe_dir/"data"/"app_config.json",exe_dir/"config"/"app_config.json"):
                if candidate.exists():return candidate
        try:
            from core.storage_path_manager import program_data_root,StoragePaths
            bootstrap=program_data_root()/"bootstrap.json"
            if bootstrap.exists():
                configured=StoragePaths.load(bootstrap).config_path
                if configured.exists():return configured
        except Exception:
            pass
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative_path

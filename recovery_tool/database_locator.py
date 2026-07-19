import os
from pathlib import Path
from core.storage_path_manager import StoragePaths,detect_legacy_storage,program_data_root


def locate_databases(exe_dir=None):
    found=[];bootstrap=program_data_root()/"bootstrap.json"
    if bootstrap.exists():
        try:found.append(StoragePaths.load(bootstrap).database_path)
        except Exception:pass
    roots=[Path(exe_dir or Path.cwd()),program_data_root(),Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"ATG_PC_AUDIT"]
    for root in roots:
        for relative in ("atg_pc_audit_master.db","data/atg_pc_audit_master.db","database/atg_pc_audit_master.db","Data/database/atg_pc_audit_master.db"):
            found.append(root/relative)
    unique=[]
    for path in found:
        if path.is_file() and path.resolve() not in [x.resolve() for x in unique]:unique.append(path)
    return unique

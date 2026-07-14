import json,shutil,tempfile,zipfile
from datetime import datetime
from pathlib import Path

def backup_database(db_path,output_dir):
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True);target=output_dir/f"ATG_PC_AUDIT_BACKUP_{datetime.now():%Y%m%d_%H%M%S}.zip"
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as z:z.write(db_path,"atg_pc_audit_master.db");z.writestr("manifest.json",json.dumps({"type":"ATG_PC_AUDIT_DATABASE_BACKUP","version":1,"created_at":datetime.now().isoformat()}))
    return target

def restore_database(zip_path,db_path):
    with zipfile.ZipFile(zip_path) as z:
        if "manifest.json" not in z.namelist() or "atg_pc_audit_master.db" not in z.namelist():raise ValueError("File ZIP không đúng cấu trúc backup ATG PC AUDIT.")
        manifest=json.loads(z.read("manifest.json"));
        if manifest.get("type")!="ATG_PC_AUDIT_DATABASE_BACKUP":raise ValueError("Manifest backup không hợp lệ.")
        db_path=Path(db_path);safety=db_path.with_suffix(f".before_restore_{datetime.now():%Y%m%d_%H%M%S}.db")
        if db_path.exists():shutil.copy2(db_path,safety)
        temp=Path(tempfile.mkdtemp())/"restore.db";temp.write_bytes(z.read("atg_pc_audit_master.db"));shutil.move(str(temp),db_path)
    return safety

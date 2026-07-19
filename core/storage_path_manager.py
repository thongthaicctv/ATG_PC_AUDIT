import json,os,shutil,tempfile
from dataclasses import asdict,dataclass
from datetime import datetime
from pathlib import Path


def program_data_root():return Path(os.environ.get("PROGRAMDATA",r"C:\ProgramData"))/"ATG_PC_AUDIT"


@dataclass
class StoragePaths:
    bootstrap_path: Path
    data_root: Path
    database_path: Path
    config_path: Path
    logs_path: Path
    exports_path: Path
    backup_root: Path
    schema_version: int=1

    @classmethod
    def defaults(cls):
        base=program_data_root();root=base/"Data"
        return cls(base/"bootstrap.json",root,root/"database"/"atg_pc_audit_master.db",root/"config"/"app_config.json",root/"logs",root/"exports",base/"Backups")
    @classmethod
    def load(cls,bootstrap_path=None):
        path=Path(bootstrap_path) if bootstrap_path else program_data_root()/"bootstrap.json"
        data=json.loads(path.read_text(encoding="utf-8"));root=Path(data["data_root"])
        return cls(path,root,Path(data["database_path"]),Path(data["config_path"]),root/"logs",root/"exports",Path(data["backup_root"]),int(data.get("schema_version",1)))
    def ensure_directories(self):
        for path in (self.data_root,self.database_path.parent,self.config_path.parent,self.logs_path,self.exports_path,self.backup_root):path.mkdir(parents=True,exist_ok=True)
    def save(self):
        self.bootstrap_path.parent.mkdir(parents=True,exist_ok=True);payload={"schema_version":self.schema_version,"data_root":str(self.data_root),"database_path":str(self.database_path),"config_path":str(self.config_path),"backup_root":str(self.backup_root),"last_updated":datetime.now().astimezone().isoformat(timespec="seconds")};atomic_json_write(self.bootstrap_path,payload);return self.bootstrap_path


def atomic_json_write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+".tmp");bak=path.with_suffix(path.suffix+".bak")
    if path.exists():shutil.copy2(path,bak)
    encoded=json.dumps(data,ensure_ascii=False,indent=2).encode("utf-8")
    with tmp.open("wb") as handle:handle.write(encoded);handle.flush();os.fsync(handle.fileno())
    json.loads(tmp.read_text(encoding="utf-8"));os.replace(tmp,path)


def validate_root(path,backup=False):
    path=Path(path);warnings=[];text=str(path).lower();temp=str(Path(tempfile.gettempdir())).lower()
    if text.startswith("\\\\"):warnings.append("Đường dẫn mạng/UNC không phù hợp để chạy SQLite trực tiếp.")
    if any(x in text for x in ("onedrive","dropbox","google drive")):warnings.append("Thư mục đồng bộ đám mây có thể gây lỗi khóa SQLite.")
    if not backup and ("program files" in text or "\\windows" in text or text.startswith(temp)):warnings.append("Không nên lưu database trong Program Files, Windows hoặc thư mục tạm.")
    path.mkdir(parents=True,exist_ok=True);probe=path/".atg_write_test";probe.write_text("ok",encoding="utf-8");probe.unlink();free=shutil.disk_usage(path).free
    if free<100*1024*1024:warnings.append("Dung lượng trống dưới 100 MB.")
    return warnings


def detect_legacy_storage(project_root=None):
    base=program_data_root();local=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"ATG_PC_AUDIT";candidates=[base/"data"/"atg_pc_audit_master.db",local/"data"/"atg_pc_audit_master.db"]
    if project_root:
        root=Path(project_root);candidates += [root/"data"/"atg_pc_audit_master.db",root/"database"/"atg_pc_audit_master.db",root/"atg_pc_audit_master.db"]
    return [p for p in candidates if p.is_file()]


def active_storage():
    bootstrap=program_data_root()/"bootstrap.json"
    if bootstrap.exists():return StoragePaths.load(bootstrap)
    legacy=detect_legacy_storage(Path(__file__).resolve().parents[1]);paths=StoragePaths.defaults()
    if legacy:paths.database_path=legacy[0]
    return paths


def open_directory(path):os.startfile(str(Path(path)))

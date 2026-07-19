import hashlib,json,os,shutil,socket,tempfile,zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from database.database_manager import DatabaseManager
from core.storage_path_manager import StoragePaths,active_storage,atomic_json_write


@dataclass
class BackupResult:
    success:bool
    backup_path:str=""
    database_size:int=0
    created_at:str=""
    checksum:str=""
    error_message:str=""


def _sha(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):digest.update(block)
    return digest.hexdigest()


def create_backup(db_path=None,output_dir=None,config_path=None,bootstrap_path=None,auth_path=None,prefix="ATG_PC_AUDIT_BACKUP"):
    paths=active_storage();db_path=Path(db_path or paths.database_path);output_dir=Path(output_dir or paths.backup_root);config_path=Path(config_path or paths.config_path);bootstrap_path=Path(bootstrap_path or paths.bootstrap_path);output_dir.mkdir(parents=True,exist_ok=True);created=datetime.now().astimezone().isoformat(timespec="seconds");target=output_dir/f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.atgbackup"
    work=Path(tempfile.mkdtemp(prefix="atg_backup_"))
    try:
        db_copy=work/"database"/db_path.name;db_copy.parent.mkdir(parents=True);manager=DatabaseManager(db_path);manager.create_consistent_backup(db_copy);validation=manager.validate_database(db_copy)
        files={f"database/{db_path.name}":db_copy}
        if config_path.is_file():dest=work/"config"/"app_config.json";dest.parent.mkdir(parents=True);shutil.copy2(config_path,dest);files["config/app_config.json"]=dest
        if bootstrap_path.is_file():
            raw=json.loads(bootstrap_path.read_text(encoding="utf-8"));normalized={"schema_version":raw.get("schema_version",1),"database_filename":db_path.name,"config_filename":"app_config.json","backup_root_configured":bool(raw.get("backup_root"))};dest=work/"bootstrap_normalized.json";dest.write_text(json.dumps(normalized,ensure_ascii=False,indent=2),encoding="utf-8");files["bootstrap_normalized.json"]=dest
        auth=Path(auth_path) if auth_path else Path(os.environ.get("PROGRAMDATA",r"C:\ProgramData"))/"ATG_PC_AUDIT"/"security"/"admin_auth.json"
        if auth.is_file():dest=work/"security"/"admin_auth.json";dest.parent.mkdir(parents=True);shutil.copy2(auth,dest);files["security/admin_auth.json"]=dest
        checksums={name:_sha(path) for name,path in files.items()};manifest={"backup_format_version":1,"application":"ATG PC AUDIT","application_version":"1.0.0","created_at":created,"computer_name":socket.gethostname(),"database_filename":db_path.name,"database_schema_version":12,"record_counts":validation.record_counts,"includes_config":"config/app_config.json" in files,"includes_admin_auth":"security/admin_auth.json" in files}
        manifest_path=work/"manifest.json";manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8");checksums_path=work/"checksums.json";checksums_path.write_text(json.dumps(checksums,indent=2),encoding="utf-8")
        with zipfile.ZipFile(target.with_suffix(".tmp"),"w",zipfile.ZIP_DEFLATED) as archive:
            archive.write(manifest_path,"manifest.json");archive.write(checksums_path,"checksums.json")
            for name,path in files.items():archive.write(path,name)
        os.replace(target.with_suffix(".tmp"),target);result=validate_backup(target)
        if not result.success:target.unlink(missing_ok=True);return result
        return BackupResult(True,str(target),db_copy.stat().st_size,created,_sha(target),"")
    except Exception as exc:target.unlink(missing_ok=True);return BackupResult(False,error_message=str(exc),created_at=created)
    finally:shutil.rmtree(work,ignore_errors=True)


def validate_backup(backup_path):
    path=Path(backup_path);work=Path(tempfile.mkdtemp(prefix="atg_validate_"))
    try:
        with zipfile.ZipFile(path) as archive:
            names=set(archive.namelist())
            if not {"manifest.json","checksums.json"}.issubset(names):raise ValueError("Backup thiếu manifest hoặc checksums.")
            manifest=json.loads(archive.read("manifest.json"));checksums=json.loads(archive.read("checksums.json"))
            if manifest.get("application")!="ATG PC AUDIT" or manifest.get("backup_format_version")!=1:raise ValueError("Manifest backup không hợp lệ.")
            database_name="database/"+manifest["database_filename"]
            if database_name not in names:raise ValueError("Backup thiếu database.")
            archive.extractall(work)
        for name,expected in checksums.items():
            if _sha(work/name)!=expected:raise ValueError("Checksum không khớp: "+name)
        validation=DatabaseManager().validate_database(work/database_name)
        if not validation.valid:raise ValueError(validation.error_message)
        return BackupResult(True,str(path),(work/database_name).stat().st_size,manifest.get("created_at",""),_sha(path),"")
    except Exception as exc:return BackupResult(False,str(path),error_message=str(exc))
    finally:shutil.rmtree(work,ignore_errors=True)


def restore_backup(backup_path,database_path,config_path=None,bootstrap_paths=None,auth_path=None):
    check=validate_backup(backup_path)
    if not check.success:raise ValueError(check.error_message)
    work=Path(tempfile.mkdtemp(prefix="atg_restore_"));database_path=Path(database_path)
    try:
        with zipfile.ZipFile(backup_path) as archive:archive.extractall(work)
        manifest=json.loads((work/"manifest.json").read_text(encoding="utf-8"));source=work/"database"/manifest["database_filename"];database_path.parent.mkdir(parents=True,exist_ok=True)
        safety=database_path.with_suffix(f".before_restore_{datetime.now():%Y%m%d_%H%M%S}.db")
        if database_path.exists():
            current=DatabaseManager(database_path).validate_database(database_path)
            if current.valid:DatabaseManager(database_path).create_consistent_backup(safety)
            else:shutil.copy2(database_path,safety)
        temp_target=database_path.with_suffix(".restore.tmp");DatabaseManager(source).create_consistent_backup(temp_target);os.replace(temp_target,database_path)
        if config_path and (work/"config"/"app_config.json").is_file():shutil.copy2(work/"config"/"app_config.json",config_path)
        if auth_path and (work/"security"/"admin_auth.json").is_file():Path(auth_path).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(work/"security"/"admin_auth.json",auth_path)
        if bootstrap_paths:bootstrap_paths.save()
        return safety
    finally:shutil.rmtree(work,ignore_errors=True)


def list_backups(root):return sorted(Path(root).glob("*.atgbackup"),key=lambda p:p.stat().st_mtime,reverse=True)
def get_latest_valid_backup(root):return next((p for p in list_backups(root) if validate_backup(p).success),None)
def cleanup_old_backups(root,keep_count=30,keep_days=90):
    items=list_backups(root);cutoff=datetime.now().timestamp()-keep_days*86400;valid=[p for p in items if validate_backup(p).success]
    for index,path in enumerate(valid):
        if index>=max(3,keep_count) and path.stat().st_mtime<cutoff:path.unlink(missing_ok=True)


def backup_database(db_path,output_dir):
    result=create_backup(db_path,output_dir)
    if not result.success:raise ValueError(result.error_message)
    return Path(result.backup_path)


def restore_database(backup_path,db_path):return restore_backup(backup_path,db_path)

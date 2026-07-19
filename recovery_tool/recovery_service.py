import getpass,json,os,socket,sqlite3
from datetime import datetime
from pathlib import Path
from core.admin_auth import auth_path,set_password
from core.backup_manager import create_backup
from core.storage_path_manager import active_storage,atomic_json_write
from database.database_manager import DatabaseManager


def account_info(auth_file=None):
    path=Path(auth_file) if auth_file else auth_path()
    if not path.exists():return {"username":"Chưa thiết lập","display_name":"","role":"AGGREGATE_ADMIN","status":"MISSING","updated_at":""}
    data=json.loads(path.read_text(encoding="utf-8"));return {"username":data.get("username","administrator"),"display_name":data.get("display_name","Quản trị viên"),"role":data.get("role","AGGREGATE_ADMIN"),"status":"ACTIVE","updated_at":data.get("updated_at","")}


def reset_password(database_path,password,confirm,must_change=True,backup_root=None,auth_file=None,config_path=None,bootstrap_path=None):
    auth_file=Path(auth_file) if auth_file else auth_path();info=account_info(auth_file);username=info["username"]
    if password!=confirm:raise ValueError("Mật khẩu nhập lại không khớp.")
    if password.strip().casefold()==username.strip().casefold():raise ValueError("Mật khẩu không được trùng tên đăng nhập.")
    manager=DatabaseManager(database_path);validation=manager.validate_database(database_path)
    if not validation.valid:raise ValueError(validation.error_message)
    storage=active_storage();root=Path(backup_root or storage.backup_root);backup=create_backup(database_path,root,config_path or storage.config_path,bootstrap_path or storage.bootstrap_path,auth_file,"BEFORE_PASSWORD_RESET")
    if not backup.success:raise ValueError("Không thể backup trước khi reset: "+backup.error_message)
    success=0
    try:
        set_password(password,auth_file.parent);data=json.loads(auth_file.read_text(encoding="utf-8"));data["username"]=username;data["display_name"]=info.get("display_name");data["role"]=info["role"];data["must_change_password"]=bool(must_change);atomic_json_write(auth_file,data);success=1
    finally:
        con=sqlite3.connect(database_path)
        try:
            con.execute("CREATE TABLE IF NOT EXISTS password_reset_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL,reset_at TEXT NOT NULL,windows_username TEXT,computer_name TEXT,reset_method TEXT NOT NULL,database_path TEXT,success INTEGER NOT NULL,note TEXT)")
            con.execute("INSERT INTO password_reset_audit(username,reset_at,windows_username,computer_name,reset_method,database_path,success,note) VALUES(?,?,?,?,?,?,?,?)",(username,datetime.now().astimezone().isoformat(timespec="seconds"),getpass.getuser(),socket.gethostname(),"recovery_tool",str(database_path),success,"Backup: "+Path(backup.backup_path).name))
            con.commit()
        finally:con.close()
    return backup.backup_path

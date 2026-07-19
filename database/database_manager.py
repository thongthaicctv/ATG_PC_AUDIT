import sqlite3
from dataclasses import dataclass,field
from pathlib import Path

# Bộ nhận diện tối thiểu phải chấp nhận database legacy (schema 1)
# để Phase 12 có thể backup an toàn trước khi chạy migration.
# sync_state/app_metadata là các bảng được bổ sung ở các phase sau.
REQUIRED_TABLES={"machines","audits","schema_info"}


@dataclass
class DatabaseValidationResult:
    valid:bool
    quick_check:str=""
    tables:set=field(default_factory=set)
    record_counts:dict=field(default_factory=dict)
    error_message:str=""


class DatabaseManager:
    def __init__(self,database_path=None):self.database_path=Path(database_path) if database_path else None
    def initialize(self,database_path):self.database_path=Path(database_path);self.database_path.parent.mkdir(parents=True,exist_ok=True)
    def close_all(self):return None
    def reconnect(self,database_path):self.close_all();self.database_path=Path(database_path)
    def connect(self,path=None):
        target=Path(path) if path else self.database_path
        if not target:raise ValueError("Chưa cấu hình database.")
        con=sqlite3.connect(target,timeout=30);con.row_factory=sqlite3.Row;con.execute("PRAGMA foreign_keys=ON");return con
    def validate_database(self,database_path=None):
        path=Path(database_path) if database_path else self.database_path
        if not path or not path.is_file():return DatabaseValidationResult(False,error_message="Không tìm thấy database.")
        try:
            if path.read_bytes()[:16]!=b"SQLite format 3\x00":return DatabaseValidationResult(False,error_message="File không có SQLite header hợp lệ.")
            con=sqlite3.connect(path)
            try:
                check=con.execute("PRAGMA quick_check").fetchone()[0];tables={x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")};counts={}
                for table in ("machines","audits","employees","conflicts"):
                    if table in tables:counts[table]=con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                if "app_metadata" in tables:
                    app_id=con.execute("SELECT value FROM app_metadata WHERE key='application_id'").fetchone()
                    if app_id and app_id[0]!="ATG_PC_AUDIT":return DatabaseValidationResult(False,check,tables,counts,"Database không thuộc ATG PC AUDIT.")
            finally:con.close()
            missing=REQUIRED_TABLES-tables
            if check!="ok" or missing:return DatabaseValidationResult(False,check,tables,counts,"Database không đúng schema ATG PC AUDIT; thiếu: "+", ".join(sorted(missing)))
            return DatabaseValidationResult(True,check,tables,counts)
        except Exception as exc:return DatabaseValidationResult(False,error_message=str(exc))
    def create_consistent_backup(self,destination_path):
        if not self.database_path:raise ValueError("Chưa cấu hình database nguồn.")
        destination=Path(destination_path);destination.parent.mkdir(parents=True,exist_ok=True)
        source=sqlite3.connect(self.database_path);target=sqlite3.connect(destination)
        try:source.backup(target)
        finally:target.close();source.close()
        result=self.validate_database(destination)
        if not result.valid:destination.unlink(missing_ok=True);raise ValueError(result.error_message or "Database backup không hợp lệ.")
        return destination

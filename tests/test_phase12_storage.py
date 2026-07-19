import json,tempfile,unittest,zipfile
from pathlib import Path
from core.aggregate_database import AggregateDatabase
from core.backup_manager import create_backup,restore_backup,validate_backup
from core.storage_path_manager import StoragePaths,atomic_json_write
from core.auth.password_hasher import hash_password,needs_rehash,verify_password as verify_encoded
from database.database_manager import DatabaseManager
from core.admin_auth import set_password,verify_password
from recovery_tool.recovery_service import reset_password


class Phase12StorageTests(unittest.TestCase):
    def test_bootstrap_atomic_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=StoragePaths(root/"bootstrap.json",root/"Data",root/"Data/database/atg_pc_audit_master.db",root/"Data/config/app_config.json",root/"Data/logs",root/"Data/exports",root/"Backups");paths.ensure_directories();paths.save();loaded=StoragePaths.load(paths.bootstrap_path);self.assertEqual(loaded.database_path,paths.database_path);self.assertFalse((root/"bootstrap.json.tmp").exists())
    def test_password_hasher(self):
        stored=hash_password("Secure123");self.assertTrue(verify_encoded("Secure123",stored));self.assertFalse(verify_encoded("bad",stored));self.assertFalse(needs_rehash(stored));self.assertNotIn("Secure123",stored)
    def test_backup_manifest_checksum_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);db=AggregateDatabase(root/"source.db");config=root/"app_config.json";atomic_json_write(config,{"phase":12});bootstrap=root/"bootstrap.json";atomic_json_write(bootstrap,{"schema_version":1,"data_root":str(root),"database_path":str(db.path),"config_path":str(config),"backup_root":str(root/"backups")});result=create_backup(db.path,root/"backups",config,bootstrap,root/"missing_auth.json");self.assertTrue(result.success,result.error_message);self.assertTrue(result.backup_path.endswith(".atgbackup"));self.assertTrue(validate_backup(result.backup_path).success);target=root/"restored.db";restore_backup(result.backup_path,target);self.assertTrue(DatabaseManager().validate_database(target).valid)
            tampered=root/"tampered.atgbackup"
            with zipfile.ZipFile(result.backup_path) as source,zipfile.ZipFile(tampered,"w") as out:
                for name in source.namelist():out.writestr(name,b"changed" if name.startswith("database/") else source.read(name))
            self.assertFalse(validate_backup(tampered).success)
    def test_non_atg_sqlite_is_rejected(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"other.db";con=sqlite3.connect(path);con.execute("CREATE TABLE unrelated(id INTEGER)");con.close();self.assertFalse(DatabaseManager().validate_database(path).valid)
    def test_recovery_resets_password_only_after_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);db=AggregateDatabase(root/"db.sqlite");security=root/"security";auth=set_password("OldSecure123",security);config=root/"app_config.json";atomic_json_write(config,{"phase":12});bootstrap=root/"bootstrap.json";atomic_json_write(bootstrap,{"schema_version":1,"data_root":str(root),"database_path":str(db.path),"config_path":str(config),"backup_root":str(root/"backups")});backup=reset_password(db.path,"NewSecure456","NewSecure456",True,root/"backups",auth,config,bootstrap);self.assertTrue(Path(backup).exists());self.assertTrue(Path(backup).name.startswith("BEFORE_PASSWORD_RESET_"));self.assertTrue(verify_password("NewSecure456",security));self.assertFalse(verify_password("OldSecure123",security))
            with db.connect() as con:self.assertEqual(con.execute("SELECT COUNT(*) FROM password_reset_audit WHERE success=1").fetchone()[0],1)


if __name__=="__main__":unittest.main()

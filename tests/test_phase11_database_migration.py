import sqlite3,tempfile,unittest
from pathlib import Path
from core.aggregate_database import AggregateDatabase


class Phase11MigrationTests(unittest.TestCase):
    def test_old_database_is_migrated_without_data_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"old.db";con=sqlite3.connect(path);con.execute("CREATE TABLE machines(id INTEGER PRIMARY KEY,asset_code TEXT,computer_name TEXT,serial_number TEXT,uuid TEXT,manufacturer TEXT,model TEXT,current_audit_id INTEGER,created_at TEXT,updated_at TEXT,is_active INTEGER DEFAULT 1)");con.execute("INSERT INTO machines(asset_code,computer_name) VALUES('PC01','MAY01')");con.commit();con.close();db=AggregateDatabase(path)
            with db.connect() as con:
                columns={x[1] for x in con.execute("PRAGMA table_info(machines)")};self.assertTrue({"employee_code","row_version","last_change_seq","detail_synced"}.issubset(columns));self.assertEqual(con.execute("SELECT asset_code FROM machines").fetchone()[0],"PC01");self.assertIsNotNone(con.execute("SELECT * FROM sync_state WHERE id=1").fetchone())


if __name__=="__main__":unittest.main()

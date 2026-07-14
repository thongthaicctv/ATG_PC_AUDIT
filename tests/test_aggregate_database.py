import tempfile,unittest
from pathlib import Path
from core.aggregate_database import AggregateDatabase

class DatabaseTests(unittest.TestCase):
    def test_create_schema_and_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AggregateDatabase(Path(tmp)/"db.sqlite")
            with db.connect() as con:
                names={x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")};self.assertTrue({"machines","audits","network_interfaces","import_history","admin_change_log"}.issubset(names))
            with self.assertRaises(Exception):db.import_records([{"record":{"audit_id":"a","export_id":"e"},"action":"import"}],"b")
            with db.connect() as con:self.assertEqual(con.execute("SELECT count(*) FROM machines").fetchone()[0],0)

    def test_database_pragmas(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AggregateDatabase(Path(tmp)/"db.sqlite")
            with db.connect() as con:self.assertEqual(con.execute("PRAGMA foreign_keys").fetchone()[0],1);self.assertEqual(con.execute("PRAGMA journal_mode").fetchone()[0].lower(),"wal")

    def test_schema_version_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=AggregateDatabase(Path(tmp)/"db.sqlite")
            with db.connect() as con:self.assertEqual(con.execute("SELECT version FROM schema_info").fetchone()[0],1)

if __name__=="__main__":unittest.main()

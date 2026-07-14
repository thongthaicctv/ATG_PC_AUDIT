import csv,tempfile,unittest
from pathlib import Path
from core.aggregate_database import AggregateDatabase
from core.csv_exporter import CSV_FIELDS,canonical_hash,export_csv
from core.csv_importer import import_previews,preview_files,scan_csv_files
from test_export import sample_result

class CsvImporterTests(unittest.TestCase):
    def test_preview_import_duplicate_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);db=AggregateDatabase(root/"master.db");p=export_csv(sample_result(),root/"csv")
            preview=preview_files([p],db);self.assertEqual(preview[0].status,"Máy mới");self.assertTrue(preview[0].hash_verified);self.assertEqual(import_previews(preview,db),1)
            again=preview_files([p],db);self.assertEqual(again[0].status,"Lần kiểm tra đã tồn tại")
            with p.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
            rows[0]["department"]="Changed"
            with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=CSV_FIELDS,quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(rows)
            tampered=preview_files([p],None);self.assertEqual(tampered[0].status,"Hash không khớp")
    def test_missing_header_and_multiple_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad=Path(tmp)/"bad.csv";bad.write_text("a,b\n1,2",encoding="utf-8");self.assertEqual(preview_files([bad])[0].status,"Thiếu cột")
            p=export_csv(sample_result(),Path(tmp));text=p.read_text(encoding="utf-8-sig");lines=text.splitlines(True);p.write_text("".join(lines+lines[1:]),encoding="utf-8-sig");items=preview_files([p]);self.assertGreaterEqual(len(items),2)

    def test_folder_scan_is_recursive(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=export_csv(sample_result(),Path(tmp)/"a"/"b");self.assertIn(p.resolve(),scan_csv_files([Path(tmp)]))

    def test_wrong_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=export_csv(sample_result(),Path(tmp));
            with p.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
            rows[0]["schema_version"]="99.0";rows[0]["record_sha256"]=canonical_hash(rows[0])
            with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=CSV_FIELDS,quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(rows)
            self.assertIn("Sai schema",preview_files([p])[0].status)

    def test_duplicate_export_id_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);db=AggregateDatabase(root/"db");p=export_csv(sample_result(),root);items=preview_files([p],db);import_previews(items,db)
            with p.open(encoding="utf-8-sig",newline="") as f:row=next(csv.DictReader(f))
            row["audit_id"]="new-audit";row["record_sha256"]=canonical_hash(row);copy=root/"copy.csv"
            with copy.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=CSV_FIELDS,quoting=csv.QUOTE_ALL);w.writeheader();w.writerow(row)
            self.assertEqual(preview_files([copy],db)[0].status,"File xuất đã được import trước đó")

if __name__=="__main__":unittest.main()

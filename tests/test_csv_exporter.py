import csv,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from core.csv_exporter import build_csv_record,canonical_hash,default_export_directory,escape_excel_formula,export_csv
from test_export import sample_result

class CsvExporterTests(unittest.TestCase):
    def test_utf8_bom_vietnamese_comma_newline_and_hash(self):
        r=sample_result();r.metadata.update(asset_code="TS-001",user="Nguyễn Văn A",notes="Có dấu phẩy, và\nxuống dòng")
        with tempfile.TemporaryDirectory() as tmp:
            p=export_csv(r,Path(tmp));self.assertTrue(p.read_bytes().startswith(b"\xef\xbb\xbf"))
            with p.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),1);self.assertEqual(rows[0]["assigned_user"],"Nguyễn Văn A");self.assertIn("\n",rows[0]["note"]);self.assertEqual(canonical_hash(rows[0]),rows[0]["record_sha256"])
    def test_formula_injection_and_privacy(self):
        r=sample_result();r.metadata.update(asset_code="=CMD",user="+SUM(1,1)");row=build_csv_record(r)
        self.assertTrue(row["asset_code"].startswith("'="));self.assertNotIn("secret@example.com",row["office_license_details_json"]);self.assertNotIn("SECRET",row["office_license_details_json"])
        self.assertNotIn("AAAAA-BBBBB-CCCCC-DDDDD",str(row))
    def test_default_folder_renames_legacy_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);exe=root/"ATG_PC_AUDIT.exe";(root/"KetQuaThuThap").mkdir()
            with patch("core.csv_exporter.sys.frozen",True,create=True),patch("core.csv_exporter.sys.executable",str(exe)):
                folder=default_export_directory()
            self.assertEqual(folder,root/"Kết quả kiểm tra");self.assertTrue(folder.is_dir());self.assertFalse((root/"KetQuaThuThap").exists())

if __name__=="__main__":unittest.main()
